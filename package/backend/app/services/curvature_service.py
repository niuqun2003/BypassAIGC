"""
Fast-DetectGPT 条件概率曲率检测 (Layer 3)

核心思想（Bao et al., ICLR 2024）：
  AI 文本的 token 选择集中于高条件概率位置 → 正曲率
  人类文本的 token 选择更分散           → 接近零曲率

黑盒实现：通过 chat completions API 的 logprobs + top_logprobs，
  使用"逐字复制"指令让模型在 temperature=1 下生成，
  从每个位置的 logprobs 估算条件概率分布，
  计算实际 token 概率与分布期望的差值（曲率）。

限制说明：
  - top_logprobs 最多 20 个 token，是完整词表分布的近似
  - 不同 API 端点对 logprobs 的支持程度不同，降级处理见 curvature_score()
"""
import math
from typing import Dict, List, Optional

from openai import AsyncOpenAI


# ─────────────────────────────────────────────────────────
# 内部工具函数
# ─────────────────────────────────────────────────────────

def _build_copy_messages(text: str, max_chars: int) -> List[Dict[str, str]]:
    """构造'逐字复制'指令消息列表，截断至 max_chars。"""
    excerpt = text[:max_chars]
    return [
        {
            "role": "system",
            "content": (
                "你是一个文本复制工具。"
                "请将用户提供的文本逐字原样输出，不得修改、增删或重排任何内容。"
            ),
        },
        {"role": "user", "content": excerpt},
    ]


def _compute_curvature_from_logprobs(token_logprobs: List) -> Optional[Dict]:
    """
    从 API 返回的 logprobs 列表计算条件概率曲率。

    每个元素含：
      .logprob        : float  — 实际生成 token 的 log p
      .top_logprobs   : list   — 每项有 .logprob 属性（top-20）

    算法（Fast-DetectGPT 公式）：
      curvature_j = log p(x_j | ctx) − E_{x̃~p(·|ctx)}[log p(x̃ | ctx)]
      E[log p] 用 top-k 重归一化后的加权期望估算
      normalized  = mean(curvature_j) / std(curvature_j)

    返回：统计字典，或 None（有效 token 数 < 10）。
    """
    actual_lps: List[float] = []
    expected_lps: List[float] = []
    per_token_sample: List[Dict] = []

    for td in token_logprobs:
        actual_lp = td.logprob
        # 跳过极低概率 token（通常是特殊 token）
        if actual_lp is None or actual_lp < -80:
            continue
        actual_lps.append(actual_lp)

        top = td.top_logprobs
        if not top:
            expected_lps.append(actual_lp)
            continue

        # 用 top-k logprobs 估算 E[log p(x̃ | context)]
        raw_lps = [t.logprob for t in top if t.logprob is not None and t.logprob > -80]
        if not raw_lps:
            expected_lps.append(actual_lp)
            continue

        # 数值稳定的 softmax + 加权期望
        max_lp = max(raw_lps)
        probs = [math.exp(lp - max_lp) for lp in raw_lps]
        total = sum(probs)
        if total < 1e-12:
            expected_lps.append(actual_lp)
            continue

        mu_hat = sum((p / total) * lp for p, lp in zip(probs, raw_lps))
        expected_lps.append(mu_hat)

        # 保存前 50 个 token 的详情
        if len(per_token_sample) < 50:
            per_token_sample.append({
                "actual_logprob":   round(actual_lp, 4),
                "expected_logprob": round(mu_hat, 4),
                "curvature":        round(actual_lp - mu_hat, 4),
            })

    n = min(len(actual_lps), len(expected_lps))
    if n < 10:
        return None

    curvatures = [actual_lps[i] - expected_lps[i] for i in range(n)]
    mean_curv = sum(curvatures) / n
    variance = sum((c - mean_curv) ** 2 for c in curvatures) / n
    std_curv = math.sqrt(variance) if variance > 0 else 1e-6

    # 归一化曲率（论文公式）
    normalized = mean_curv / std_curv

    # sigmoid 映射到 0-1 AI 风险分
    # 中心 c=1.0：人类文本曲率≈0 → 风险≈18%；AI 文本曲率≈2+ → 风险≈82%+
    ai_risk = 1.0 / (1.0 + math.exp(-1.5 * (normalized - 1.0)))

    return {
        "mean_curvature":        round(mean_curv, 4),
        "std_curvature":         round(std_curv, 4),
        "normalized_curvature":  round(normalized, 4),
        "ai_risk":               round(ai_risk, 4),
        "ai_risk_percent":       int(ai_risk * 100),
        "token_count":           n,
        "per_token_sample":      per_token_sample,
    }


# ─────────────────────────────────────────────────────────
# 公共入口
# ─────────────────────────────────────────────────────────

_UNAVAILABLE = {"available": False, "method": "fast-detectgpt-logprobs", "ai_risk_percent": None}


async def curvature_score(
    text: str,
    model: str,
    api_key: str,
    base_url: str,
    max_chars: int = 2000,
) -> Dict:
    """
    Layer 3 公共入口：Fast-DetectGPT 条件概率曲率分数。

    成功::
        {available: True, ai_risk_percent: int, normalized_curvature: float,
         mean_curvature: float, std_curvature: float, token_count: int,
         per_token_sample: list, method: str}

    失败（降级，不影响 Layer 1/2）::
        {available: False, error: str, method: str, ai_risk_percent: None}
    """
    if not (api_key and base_url and model):
        return {**_UNAVAILABLE, "error": "未配置 API（model/api_key/base_url 缺失）"}

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=35.0,
        max_retries=0,
    )
    messages = _build_copy_messages(text, max_chars)

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=1.0,                          # 保留原始分布，不贪心采样
            max_tokens=min(len(text) + 100, 1500),
            logprobs=True,
            top_logprobs=20,                          # API 最大值
        )
    except Exception as e:
        msg = str(e).lower()
        if any(kw in msg for kw in ("logprob", "not support", "unsupport", "invalid_request")):
            return {**_UNAVAILABLE, "error": "API 不支持 logprobs 参数"}
        return {**_UNAVAILABLE, "error": f"API 调用失败: {str(e)[:120]}"}

    choice = resp.choices[0] if resp.choices else None
    if not choice or not choice.logprobs or not choice.logprobs.content:
        return {**_UNAVAILABLE, "error": "模型未返回 logprobs 数据（该模型可能不支持）"}

    stats = _compute_curvature_from_logprobs(choice.logprobs.content)
    if stats is None:
        return {**_UNAVAILABLE, "error": "有效 token 数不足（< 10），文本可能过短"}

    return {
        "available": True,
        "method":    "fast-detectgpt-logprobs",
        **stats,
    }
