"""
AIGC 检测服务
两层检测：
  Layer 1 - 文体特征（本地计算，零成本）
  Layer 2 - LLM 判分（Fast-DetectGPT 简化版，调用已有 API）
"""
import re
import math
import json
import asyncio
from typing import List, Dict, Optional, Tuple

from openai import AsyncOpenAI
from app.config import settings


# ─────────────────────────────────────────────────────────
# 文本预处理
# ─────────────────────────────────────────────────────────

def split_sentences(text: str) -> List[str]:
    """中英文句子分割"""
    parts = re.split(r'[。！？!?；;]+', text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]


def split_paragraphs(text: str) -> List[str]:
    """按空行或标题拆段"""
    paras = re.split(r'\n\s*\n|\n(?=[一二三四五六七八九十\d][\s、．.。])', text)
    return [p.strip() for p in paras if p.strip() and len(p.strip()) > 20]


def simple_tokenize(text: str) -> List[str]:
    """
    轻量级分词（无外部依赖）：
    - 中文：每个字作为 token
    - 英文：按空格+标点切词
    """
    tokens: List[str] = []
    word = ""
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf':
            if word:
                tokens.append(word.lower())
                word = ""
            tokens.append(ch)
        elif ch.isalpha() or ch == "'":
            word += ch
        else:
            if word:
                tokens.append(word.lower())
                word = ""
    if word:
        tokens.append(word.lower())
    return tokens


# ─────────────────────────────────────────────────────────
# Layer 1：文体特征
# ─────────────────────────────────────────────────────────

def _burstiness(sentences: List[str]) -> Tuple[float, float]:
    """
    突发度 = 句长变异系数 (std/mean)。
    AI 文本句长均匀 → burstiness 低 → AI 风险分高。
    返回 (burstiness_raw, ai_risk_score 0-1)
    """
    if len(sentences) < 3:
        return 0.5, 0.4
    lengths = [len(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean < 1:
        return 0.5, 0.4
    std = math.sqrt(sum((l - mean) ** 2 for l in lengths) / len(lengths))
    bursty = std / mean  # 人类 0.4-1.0，AI 0.1-0.4
    # 映射：burstiness=0 → risk=1；burstiness=0.8 → risk=0
    risk = max(0.0, min(1.0, 1.0 - bursty / 0.7))
    return round(bursty, 3), round(risk, 3)


def _type_token_ratio(tokens: List[str]) -> Tuple[float, float]:
    """
    词汇多样性。TTR 越低 → 词汇重复 → AI 风险高。
    为了对长文本公平，用移动窗口 TTR（MATTR，窗口=100）。
    返回 (ttr_raw, ai_risk_score 0-1)
    """
    if len(tokens) < 10:
        return 0.5, 0.4
    window = 100
    if len(tokens) <= window:
        ttr = len(set(tokens)) / len(tokens)
    else:
        windows = [tokens[i:i + window] for i in range(0, len(tokens) - window + 1, window // 2)]
        ttr = sum(len(set(w)) / len(w) for w in windows) / len(windows)
    # 学术文本 TTR 自然偏低，AI 更低；阈值偏保守
    risk = max(0.0, min(1.0, (0.7 - ttr) / 0.4))
    return round(ttr, 3), round(risk, 3)


# 学术中文高频 AI 连接词
_CN_CONNECTORS = [
    '因此', '然而', '此外', '总之', '综上所述', '综上', '由此可见',
    '首先', '其次', '再次', '最后', '同时', '另外', '总体而言',
    '值得注意的是', '不仅如此', '与此同时', '总的来说', '简而言之',
    '换言之', '进一步', '具体而言', '相比之下', '由上可知',
]
_EN_CONNECTORS = [
    'furthermore', 'moreover', 'however', 'therefore', 'in conclusion',
    'in summary', 'additionally', 'consequently', 'nevertheless',
    'in addition', 'on the other hand', 'as a result', 'thus', 'hence',
    'in contrast', 'specifically', 'in particular', 'notably',
]


def _connector_density(text: str) -> Tuple[float, float]:
    """
    连接词密度（per 1000字）。AI 论文过度使用规范连接词。
    返回 (density_raw, ai_risk_score 0-1)
    """
    text_lower = text.lower()
    count = sum(1 for c in _CN_CONNECTORS if c in text)
    count += sum(1 for c in _EN_CONNECTORS if c in text_lower)
    per_1k = count / max(len(text) / 1000, 0.5)
    # 3个/千字 ≈ 正常学术；>6个 → AI 感强
    risk = max(0.0, min(1.0, per_1k / 8.0))
    return round(per_1k, 3), round(risk, 3)


# 典型 AI 学术句式
_AI_PATTERNS = [
    r'[\u4e00-\u9fff]{2,}是[\u4e00-\u9fff]{2,}',      # X是Y
    r'[\u4e00-\u9fff]{2,}具有[\u4e00-\u9fff]{2,}',     # X具有Y
    r'[\u4e00-\u9fff]{2,}表明[\u4e00-\u9fff]{2,}',     # X表明Y
    r'[\u4e00-\u9fff]{2,}需要[\u4e00-\u9fff]{2,}',     # X需要Y
    r'[\u4e00-\u9fff]{2,}可以[\u4e00-\u9fff]{2,}',     # X可以Y
    r'[\u4e00-\u9fff]{2,}有助于[\u4e00-\u9fff]{2,}',   # X有助于Y
    r'[\u4e00-\u9fff]{2,}体现了[\u4e00-\u9fff]{2,}',   # X体现了Y
    r'[\u4e00-\u9fff]{2,}发挥[\u4e00-\u9fff]{1,}作用',  # 发挥X作用
]


def _sentence_uniformity(sentences: List[str]) -> Tuple[float, float]:
    """
    AI 句式单一性：检测模板化句式占比。
    返回 (uniformity_raw, ai_risk_score 0-1)
    """
    if not sentences:
        return 0.5, 0.4
    matches = sum(
        1 for s in sentences
        if any(re.search(p, s) for p in _AI_PATTERNS)
    )
    ratio = matches / len(sentences)
    risk = min(ratio * 1.5, 1.0)
    return round(ratio, 3), round(risk, 3)


def _paragraph_length_variance(paragraphs: List[str]) -> Tuple[float, float]:
    """
    段落长度方差。AI 段落往往长度整齐。
    返回 (cv_raw, ai_risk_score 0-1)
    """
    if len(paragraphs) < 2:
        return 0.5, 0.3
    lengths = [len(p) for p in paragraphs]
    mean = sum(lengths) / len(lengths)
    if mean < 1:
        return 0.5, 0.3
    std = math.sqrt(sum((l - mean) ** 2 for l in lengths) / len(lengths))
    cv = std / mean
    risk = max(0.0, min(1.0, 1.0 - cv / 0.8))
    return round(cv, 3), round(risk, 3)


# 权重（文体特征内部）
_STYLO_WEIGHTS = {
    'burstiness': 0.30,
    'ttr': 0.20,
    'connector': 0.25,
    'uniformity': 0.15,
    'para_var': 0.10,
}


def analyze_stylometric(text: str) -> Dict:
    """
    计算全部文体特征，返回特征值和整体 ai_score (0-1)。
    """
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)
    tokens = simple_tokenize(text)

    bursty_raw, bursty_risk = _burstiness(sentences)
    ttr_raw, ttr_risk = _type_token_ratio(tokens)
    conn_raw, conn_risk = _connector_density(text)
    unif_raw, unif_risk = _sentence_uniformity(sentences)
    pvar_raw, pvar_risk = _paragraph_length_variance(paragraphs)

    score = (
        bursty_risk * _STYLO_WEIGHTS['burstiness'] +
        ttr_risk    * _STYLO_WEIGHTS['ttr'] +
        conn_risk   * _STYLO_WEIGHTS['connector'] +
        unif_risk   * _STYLO_WEIGHTS['uniformity'] +
        pvar_risk   * _STYLO_WEIGHTS['para_var']
    )

    return {
        'ai_score': round(score, 3),
        'features': {
            'burstiness':         {'value': bursty_raw, 'risk': bursty_risk, 'label': '突发度（低=AI）'},
            'type_token_ratio':   {'value': ttr_raw,   'risk': ttr_risk,    'label': '词汇多样性（低=AI）'},
            'connector_density':  {'value': conn_raw,  'risk': conn_risk,   'label': '连接词密度（高=AI）'},
            'sentence_uniformity':{'value': unif_raw,  'risk': unif_risk,   'label': '句式单一性（高=AI）'},
            'para_length_var':    {'value': pvar_raw,  'risk': pvar_risk,   'label': '段落长度方差（低=AI）'},
        },
        'stats': {
            'sentence_count': len(sentences),
            'paragraph_count': len(paragraphs),
            'token_count': len(tokens),
            'char_count': len(text),
        },
    }


# ─────────────────────────────────────────────────────────
# Layer 1 段落级打分（仅文体特征，用于报告高亮）
# ─────────────────────────────────────────────────────────

def analyze_sections(text: str) -> List[Dict]:
    """
    对每个段落单独做文体打分。
    返回段落列表，含 text_preview / score / tier。
    """
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        paragraphs = [text]

    results = []
    for idx, para in enumerate(paragraphs):
        if len(para) < 30:
            results.append({
                'index': idx,
                'text_preview': para[:80],
                'char_count': len(para),
                'score': None,
                'tier': 'skip',
            })
            continue
        stylo = analyze_stylometric(para)
        score_100 = int(stylo['ai_score'] * 100)
        tier = _score_to_tier(score_100)
        results.append({
            'index': idx,
            'text_preview': para[:100] + ('...' if len(para) > 100 else ''),
            'char_count': len(para),
            'score': score_100,
            'tier': tier,
        })
    return results


def _score_to_tier(score: int) -> str:
    if score >= 65:
        return 'significant'
    if score >= 40:
        return 'suspected'
    return 'unmarked'


# ─────────────────────────────────────────────────────────
# Layer 2：LLM 评分（Fast-DetectGPT 简化版）
# ─────────────────────────────────────────────────────────

_LLM_PROMPT = """你是一个AIGC内容检测专家，专注于中文学术论文分析。

请仔细阅读下面的文本，从以下维度分析它是否由AI生成：
1. 句式是否单一重复、过于规整
2. 是否缺乏真实的个人经历、具体细节和情感波动
3. 连接词和过渡语是否过于程式化（如"综上所述""值得注意的是"）
4. 词汇选择是否显得机械，缺乏文字个性
5. 段落结构是否像"总-分-总"的AI模板
6. 是否有自然的语言瑕疵、口语化表达或独特视角

请只输出一个合法JSON，格式：
{{"aigc_probability": <0到100的整数>, "confidence": "<low|medium|high>", "signals": ["最多3条关键信号，每条不超过20字"]}}

不要输出任何JSON以外的内容。

待检测文本：
{text}"""


async def llm_score(
    text: str,
    model: str,
    api_key: str,
    base_url: str,
) -> Dict:
    """
    调用 LLM 对全文打 AIGC 概率分。
    失败时返回 confidence=low，score=None（不参与最终加权）。
    """
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip('/'),
        timeout=40.0,
        max_retries=1,
    )

    # 长文截断（只取前后各 1500 字，避免超限）
    excerpt = text[:1800] if len(text) <= 1800 else text[:1200] + '\n……（中间省略）……\n' + text[-600:]
    prompt = _LLM_PROMPT.format(text=excerpt)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.05,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        # 提取 JSON（有些模型会加 markdown 代码块）
        m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not m:
            raise ValueError(f'No JSON in response: {raw[:200]}')
        data = json.loads(m.group())
        prob = int(data.get('aigc_probability', 50))
        prob = max(0, min(100, prob))
        return {
            'aigc_probability': prob,
            'confidence': data.get('confidence', 'medium'),
            'signals': data.get('signals', [])[:3],
            'available': True,
        }
    except Exception as e:
        print(f'[DETECTION] LLM scoring failed: {e}')
        return {
            'aigc_probability': None,
            'confidence': 'unavailable',
            'signals': [],
            'available': False,
            'error': str(e),
        }


# ─────────────────────────────────────────────────────────
# 综合打分
# ─────────────────────────────────────────────────────────

def _final_score(stylo_score: float, llm_prob: Optional[int]) -> Tuple[int, str]:
    """
    合并文体分和 LLM 分 → 最终文档分 (0-100) + 置信度标签。
    - 只有文体分时：权重 100%，置信度降级
    - 两者都有时：文体 35% + LLM 65%
    """
    if llm_prob is None:
        final = int(stylo_score * 100)
        confidence = 'medium'
    else:
        final = int(stylo_score * 100 * 0.35 + llm_prob * 0.65)
        confidence = 'high'

    final = max(0, min(100, final))
    return final, confidence


def _tier_label(score: int) -> str:
    if score >= 65:
        return 'high'
    if score >= 40:
        return 'medium'
    return 'low'


def _tier_cn(tier: str) -> str:
    return {'high': '高风险', 'medium': '中等风险', 'low': '低风险'}.get(tier, tier)


def _section_tier_cn(tier: str) -> str:
    return {
        'significant': '显著疑似',
        'suspected': '疑似',
        'unmarked': '未标记',
        'skip': '段落过短',
    }.get(tier, tier)


# ─────────────────────────────────────────────────────────
# 公共入口
# ─────────────────────────────────────────────────────────

async def detect_text(
    text: str,
    use_llm: bool = True,
    detect_model: Optional[str] = None,
    detect_api_key: Optional[str] = None,
    detect_base_url: Optional[str] = None,
) -> Dict:
    """
    对文本执行完整 AIGC 检测，返回可直接序列化的报告 dict。

    参数
    ----
    text         : 待检测文本
    use_llm      : 是否调用 LLM 打分（需要 API Key 配置）
    detect_model : 覆盖默认检测模型（不填则用 POLISH_MODEL）
    """
    import time
    t0 = time.time()

    # — Layer 1：文体特征 —
    stylo = analyze_stylometric(text)
    sections = analyze_sections(text)

    # — Layer 2：LLM —
    llm_result: Dict = {'available': False, 'aigc_probability': None, 'confidence': 'unavailable', 'signals': []}
    if use_llm:
        model     = detect_model     or settings.DETECT_MODEL     or settings.POLISH_MODEL
        api_key   = detect_api_key   or settings.DETECT_API_KEY   or settings.POLISH_API_KEY
        base_url  = detect_base_url  or settings.DETECT_BASE_URL  or settings.POLISH_BASE_URL
        if api_key and base_url and model:
            llm_result = await llm_score(text, model, api_key, base_url)

    # — 综合 —
    doc_score, confidence = _final_score(
        stylo['ai_score'],
        llm_result.get('aigc_probability') if llm_result['available'] else None,
    )
    doc_tier = _tier_label(doc_score)

    # 统计被标记字数（significant + suspected 段落）
    flagged_chars = sum(
        s['char_count'] for s in sections
        if s.get('tier') in ('significant', 'suspected')
    )

    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        'document_score': doc_score,
        'document_tier': doc_tier,
        'document_tier_cn': _tier_cn(doc_tier),
        'confidence': confidence,
        'char_count': len(text),
        'flagged_char_count': flagged_chars,
        'processing_time_ms': elapsed_ms,
        'stylometric': {
            'ai_score': stylo['ai_score'],
            'features': stylo['features'],
            'stats': stylo['stats'],
        },
        'llm': {
            'available': llm_result['available'],
            'aigc_probability': llm_result.get('aigc_probability'),
            'confidence': llm_result.get('confidence'),
            'signals': llm_result.get('signals', []),
        },
        'sections': [
            {**s, 'tier_cn': _section_tier_cn(s['tier'])}
            for s in sections
        ],
        'risk_legend': {
            'significant': {'label': '显著疑似', 'threshold': 65, 'color': 'red'},
            'suspected':   {'label': '疑似',     'threshold': 40, 'color': 'orange'},
            'unmarked':    {'label': '未标记',   'threshold': 0,  'color': 'green'},
        },
    }
