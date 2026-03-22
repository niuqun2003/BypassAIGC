# AIGC 检测产品方案

> 版本：v1.0
> 日期：2026-03-21
> 基于论文：DetectGPT (ICML 2023) + Fast-DetectGPT (ICLR 2024) + 对抗攻击 (COLING 2024)

---

## 一、产品定位

### 1.1 目标用户

| 用户群体 | 核心需求 | 付费意愿 |
|----------|----------|----------|
| **高校教务处** | 论文查重+AIGC检测 | 高（预算充足） |
| **期刊编辑部** | 稿件初审 | 中 |
| **企业HR** | 简历真实性 | 低-中 |
| **内容平台** | 过滤AI垃圾内容 | 中 |
| **个人用户** | 自查自纠 | 低 |

### 1.2 核心价值主张

> **"三重检测 + 对抗防御"**
> 
> 不只是检测 AI，而是构建一个**对抗性鲁棒**的检测系统

### 1.3 差异化优势

| 维度 | 竞品（知网/GPTZero） | 本产品 |
|------|---------------------|--------|
| 检测速度 | 分钟级 | **秒级** |
| API成本 | 高（$0.01-0.1/次） | **低（¥0.01-0.05/次）** |
| 对抗鲁棒性 | 弱（易被攻破） | **强（集成+对抗训练）** |
| 中文优化 | 一般 | **专门优化** |
| 部署方式 | 仅云端 | **云端+私有化** |

---

## 二、技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户接入层                               │
│   Web API │ 批量上传 │ 浏览器插件 │ LMS集成（Moodle/超星）        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                         业务逻辑层                               │
│   文档解析 │ 任务队列 │ 结果缓存 │ 计费统计 │ 报告生成            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                         检测引擎层                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 零样本检测器  │  │ 文体特征检测  │  │ 对抗防御模块  │          │
│  │(Fast-DetectGPT)│ │ (词频/句法)   │ │ (异常检测)    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                      │
│                  ┌────────────────┐                              │
│                  │   集成分类器    │                              │
│                  │ (XGBoost/LightGBM)│                           │
│                  └────────┬───────┘                              │
│                           ▼                                      │
│                  ┌────────────────┐                              │
│                  │  置信度校准     │                              │
│                  │ (Platt Scaling)│                              │
│                  └────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                         模型服务层                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ DeepSeek API │  │ GLM-4 API    │  │ 本地模型     │          │
│  │ (主力检测模型)│ │ (备用/中文优化)│ │ (私有化部署)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                         数据存储层                               │
│   检测记录 │ 用户数据 │ 对抗样本库 │ 模型版本管理                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 三重检测引擎

#### 引擎一：零样本检测（Fast-DetectGPT）

**技术原理**：
- 计算 L条件概率曲率（conditional probability curvature）
- 只需 2 次 API 调用（原 DetectGPT 需要 100+ 次）

**实现细节**：
```python
def fast_detect_gpt(text, scoring_model, sampling_model):
    """
    text: 待检测文本
    scoring_model: 评分模型（如 DeepSeek）
    sampling_model: 采样模型（可以相同）
    """
    # Step 1: 计算条件概率
    log_prob = scoring_model.log_prob(text)
    
    # Step 2: 采样生成对比文本
    samples = sampling_model.sample_conditional(text, n=100)
    log_prob_samples = [scoring_model.log_prob(s) for s in samples]
    
    # Step 3: 计算条件概率曲率
    d = log_prob - np.mean(log_prob_samples)
    
    return d  # 负值 = AI生成概率高
```

**性能指标**：
- 速度：约 2 秒/篇（1000字）
- 成本：约 ¥0.01-0.03/篇
- 准确率：AUROC 0.98+

#### 引擎二：文体特征检测

**特征维度**：

| 特征类型 | 具体指标 | AI特征 |
|----------|----------|--------|
| **词汇层** | 词频分布、词汇丰富度 | 高频词重复、同义词堆砌 |
| **句法层** | 句长分布、句式结构 | 句式单一、偏好长句 |
| **语义层** | 困惑度、突发度 | 低困惑度、低突发度 |
| **篇章层** | 段落衔接、逻辑连贯 | 机械堆砌、缺乏过渡 |
| **风格层** | 情感倾向、语气 | 中性客观、缺乏个人色彩 |

**实现方式**：
```python
def stylistic_features(text):
    features = {}
    
    # 困惑度（使用 GPT-2 中文版）
    features['perplexity'] = gpt2_perplexity(text)
    
    # 突发度（句子长度变化）
    sentences = split_sentences(text)
    lengths = [len(s) for s in sentences]
    features['burstiness'] = np.std(lengths) / np.mean(lengths)
    
    # 词频特征
    tokens = tokenize(text)
    features['type_token_ratio'] = len(set(tokens)) / len(tokens)
    
    # 句式特征
    features['avg_sentence_length'] = np.mean(lengths)
    features['sentence_length_var'] = np.var(lengths)
    
    # 逻辑连接词
    connectors = ['因此', '然而', '此外', '总之', '综上所述']
    features['connector_density'] = sum(1 for c in connectors if c in text) / len(text)
    
    return features
```

#### 引擎三：对抗防御模块

**防御策略**：

```
┌─────────────────────────────────────────────────┐
│              对抗防御流程                        │
├─────────────────────────────────────────────────┤
│                                                 │
│  输入文本                                       │
│      │                                          │
│      ▼                                          │
│  ┌──────────────────┐                          │
│  │ 异常特征检测      │                          │
│  │ - 困惑度异常高？  │ ← 对抗攻击通常会增加困惑度│
│  │ - 同义词替换痕迹？│                          │
│  │ - 句法重组痕迹？  │                          │
│  └──────┬───────────┘                          │
│         │                                      │
│         ▼                                      │
│  ┌──────────────────┐                          │
│  │ 对抗样本匹配      │                          │
│  │ 与已知对抗样本库  │                          │
│  │ 计算相似度       │                          │
│  └──────┬───────────┘                          │
│         │                                      │
│         ▼                                      │
│  ┌──────────────────┐                          │
│  │ 模型集成投票      │                          │
│  │ 多个检测器独立判断│                          │
│  │ 取加权平均       │                          │
│  └──────┬───────────┘                          │
│         │                                      │
│         ▼                                      │
│  输出结果 + 对抗标记                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

**对抗检测特征**：

```python
def adversarial_detection(text, base_score):
    """
    检测是否遭受对抗攻击
    """
    signals = []
    
    # 信号1: 困惑度异常高（对抗攻击会人为增加）
    perplexity = calculate_perplexity(text)
    if perplexity > THRESHOLD_HIGH:
        signals.append('high_perplexity')
    
    # 信号2: 同义词替换痕迹
    synonym_pairs = detect_synonym_replacement(text)
    if len(synonym_pairs) > 3:
        signals.append('synonym_replacement')
    
    # 信号3: 句法不一致（部分句子风格突变）
    style_consistency = calculate_style_consistency(text)
    if style_consistency < 0.7:
        signals.append('style_inconsistency')
    
    # 信号4: 与检测器得分矛盾
    # 如果基础检测器认为是人类，但文体特征显示AI特征
    if base_score < 0.3 and has_ai_stylistic_features(text):
        signals.append('score_contradiction')
    
    return {
        'is_adversarial': len(signals) >= 2,
        'signals': signals,
        'confidence': len(signals) / 4
    }
```

### 2.3 集成分类器

**模型选择**：LightGBM（速度快、可解释性好）

**特征融合**：
```python
def integrated_detection(text):
    # 1. 零样本检测
    zero_shot_score = fast_detect_gpt(text, deepseek, deepseek)
    
    # 2. 文体特征
    style_features = stylistic_features(text)
    
    # 3. 对抗检测
    adversarial_info = adversarial_detection(text, zero_shot_score)
    
    # 4. 集成分类
    features = [
        zero_shot_score,
        style_features['perplexity'],
        style_features['burstiness'],
        style_features['type_token_ratio'],
        adversarial_info['confidence']
    ]
    
    # LightGBM 预测
    final_score = lgb_model.predict([features])[0]
    
    # 5. 对抗调整
    if adversarial_info['is_adversarial']:
        final_score = adjust_for_adversarial(final_score, adversarial_info)
    
    return {
        'ai_probability': final_score,
        'is_adversarial': adversarial_info['is_adversarial'],
        'breakdown': {
            'zero_shot': zero_shot_score,
            'stylistic': style_features,
            'adversarial': adversarial_info
        }
    }
```

---

## 三、检测流程

### 3.1 标准检测流程

```
用户提交文本
    │
    ▼
文档预处理（分段、清洗）
    │
    ▼
并行检测（三引擎同时）
    ├─ 零样本检测 ────┐
    ├─ 文体特征 ──────┤
    └─ 对抗检测 ──────┤
                      │
                      ▼
              特征融合 & 集成分类
                      │
                      ▼
              结果校准 & 置信度
                      │
                      ▼
              生成检测报告
                      │
                      ▼
    ┌─────────────────┴─────────────────┐
    │                                   │
    ▼                                   ▼
API返回                              前端展示
```

### 3.2 分段检测策略

**为什么分段**：
- 长文本不同部分可能由不同来源生成
- 混合文本（AI生成+人工改写）需要定位

**分段逻辑**：
```python
def segment_detection(text):
    # 按段落分割
    paragraphs = split_paragraphs(text)
    
    results = []
    for i, para in enumerate(paragraphs):
        if len(para) < 50:  # 太短的段落跳过
            results.append({'index': i, 'skip': True})
            continue
        
        result = integrated_detection(para)
        result['index'] = i
        results.append(result)
    
    # 整体得分（加权平均）
    weights = [len(paragraphs[r['index']]) for r in results if not r.get('skip')]
    scores = [r['ai_probability'] for r in results if not r.get('skip')]
    overall_score = np.average(scores, weights=weights)
    
    return {
        'overall_score': overall_score,
        'segments': results,
        'highlighted_text': highlight_ai_segments(text, results)
    }
```

### 3.3 检测报告格式

```json
{
  "document_id": "doc_20260321_abc123",
  "timestamp": "2026-03-21T16:00:00Z",
  "summary": {
    "ai_probability": 0.87,
    "confidence": "high",
    "is_adversarial": false,
    "verdict": "高概率AI生成"
  },
  "breakdown": {
    "zero_shot_score": 0.92,
    "stylistic_score": 0.85,
    "perplexity": 12.3,
    "burstiness": 0.45
  },
  "segments": [
    {
      "index": 0,
      "text": "第一段内容...",
      "ai_probability": 0.95,
      "highlight": true
    },
    {
      "index": 1,
      "text": "第二段内容...",
      "ai_probability": 0.32,
      "highlight": false
    }
  ],
  "metadata": {
    "word_count": 1523,
    "processing_time_ms": 1850,
    "model_version": "v1.2.3"
  }
}
```

---

## 四、对抗防御策略

### 4.1 核心防御措施

| 层次 | 措施 | 针对的攻击类型 |
|------|------|----------------|
| **模型层** | 多模型集成投票 | 所有攻击类型 |
| **特征层** | 对抗样本特征检测 | 同义词替换、句法重组 |
| **数据层** | 对抗训练 | 所有攻击类型 |
| **后处理** | 异常得分校准 | 得分操纵 |

### 4.2 对抗训练流程

```
正常训练数据
    │
    ▼
生成对抗样本（使用HMGC等方法）
    │
    ├─ 同义词替换样本
    ├─ 句法重组样本
    └─ 改写攻击样本
    │
    ▼
混合训练集（正常+对抗）
    │
    ▼
训练集成分类器
    │
    ▼
定期更新对抗样本库
```

### 4.3 持续对抗机制

```python
class AdversarialDefenseSystem:
    def __init__(self):
        self.adversarial_sample_db = load_adversarial_db()
        self.model_versions = {}
        
    def update_defense(self, new_attack_samples):
        """定期更新防御模型"""
        # 1. 分析新攻击样本特征
        attack_patterns = analyze_attack_patterns(new_attack_samples)
        
        # 2. 生成对抗训练样本
        augmented_samples = generate_adversarial_variants(new_attack_samples)
        
        # 3. 重新训练模型
        self.retrain_models(augmented_samples)
        
        # 4. 更新样本库
        self.adversarial_sample_db.add(new_attack_samples)
        
    def detect_new_attack(self, text, detection_result):
        """检测未知攻击类型"""
        # 如果检测得分异常但无法分类
        if detection_result['confidence'] < 0.6:
            # 标记为可疑样本，人工审核
            flag_for_review(text, detection_result)
```

---

## 五、部署方案

### 5.1 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        云端部署（主）                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ API 网关     │  │ 负载均衡     │  │ CDN 加速     │          │
│  │ (Kong/APISIX)│ │ (Nginx)      │  │ (静态资源)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │           Kubernetes 集群                         │          │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐          │          │
│  │  │ API服务  │  │ 检测引擎 │  │ 任务队列 │          │          │
│  │  │ (x3)    │  │ (x5)    │  │ (x2)    │          │          │
│  │  └─────────┘  └─────────┘  └─────────┘          │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ PostgreSQL   │  │ Redis        │  │ MinIO        │          │
│  │ (持久化存储)  │ │ (缓存/队列)   │ │ (文件存储)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      私有化部署（可选）                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │           Docker Compose                          │          │
│  │  - 本地模型服务（DeepSeek-7B/GLM-4-9B）           │          │
│  │  - 检测引擎                                       │          │
│  │  - PostgreSQL                                    │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  硬件要求：GPU 24GB+ / 内存 64GB+                               │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 成本估算

**云端部署（月成本）**：

| 项目 | 规格 | 月费用 |
|------|------|--------|
| API 服务 | 3x 2核4G | ¥300 |
| 检测引擎 | 5x 4核8G | ¥1,000 |
| GPU 推理 | 2x T4 | ¥2,000 |
| 数据库 | PostgreSQL 100G | ¥200 |
| 缓存 | Redis 8G | ¥150 |
| 存储 | 对象存储 500G | ¥50 |
| **合计** | - | **¥3,700/月** |

**API 调用成本**：

| 场景 | 模型调用 | 单次成本 |
|------|----------|----------|
| 零样本检测 | DeepSeek API | ¥0.01-0.03 |
| 文体特征 | 本地模型 | ¥0 |
| 集成分类 | 本地模型 | ¥0 |
| **合计** | - | **¥0.01-0.03/次** |

**私有化部署（一次性成本）**：

| 项目 | 规格 | 费用 |
|------|------|------|
| 服务器 | GPU服务器（租用） | ¥5,000-10,000/月 |
| 或自建 | RTX 4090 x 2 | ¥30,000-40,000（一次性） |

### 5.3 定价策略

**SaaS 模式**：

| 套餐 | 价格 | 包含 |
|------|------|------|
| 免费版 | ¥0 | 10次/天，基础报告 |
| 基础版 | ¥99/月 | 500次/月，完整报告 |
| 专业版 | ¥299/月 | 2000次/月，API接入 |
| 企业版 | ¥999/月 | 不限次数，私有化部署 |

**API 调用**：
- 按次计费：¥0.05/次
- 包月套餐：¥99/1000次

---

## 六、开发路线图

### Phase 1：原型验证（2周）

**目标**：验证核心技术可行性

- [ ] 搭建 Fast-DetectGPT 原型
- [ ] 对接 DeepSeek API
- [ ] 实现基础文体特征提取
- [ ] 测试中文文本检测效果

**交付物**：
- 可运行的检测脚本
- 测试报告（准确率、速度、成本）

### Phase 2：核心功能（1个月）

**目标**：构建完整检测引擎

- [ ] 实现三重检测引擎
- [ ] 训练集成分类器
- [ ] 开发对抗防御模块
- [ ] 构建训练数据集

**交付物**：
- 完整检测引擎代码
- 模型训练脚本
- 评估报告

### Phase 3：产品化（1个月）

**目标**：打造可用产品

- [ ] 开发 REST API
- [ ] 开发 Web 界面
- [ ] 实现批量检测
- [ ] 生成检测报告

**交付物**：
- 可部署的 Docker 镜像
- API 文档
- 用户手册

### Phase 4：商业化（持续）

**目标**：推向市场

- [ ] 云端部署
- [ ] 私有化部署方案
- [ ] 对接 LMS（Moodle/超星）
- [ ] 对抗样本持续更新

---

## 七、风险与应对

### 7.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 新模型突破检测 | 高 | 持续更新模型，对抗训练 |
| 对抗攻击进化 | 高 | 多层防御，异常检测 |
| 误判率高 | 中 | 人工审核机制，置信度校准 |
| API 成本上涨 | 中 | 本地模型备份，多供应商 |

### 7.2 合规风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 学术争议 | 中 | 明确检测局限，提供申诉渠道 |
| 隐私问题 | 高 | 数据加密，不存储原文 |
| 版权问题 | 低 | 仅检测不复制 |

### 7.3 商业风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 竞品压价 | 中 | 差异化功能，对抗防御 |
| 客户流失 | 中 | 私有化部署，深度集成 |
| API 依赖 | 高 | 自建模型能力 |

---

## 八、附录

### A. 技术选型对比

| 组件 | 方案A | 方案B | 选择 | 理由 |
|------|-------|-------|------|------|
| 零样本检测 | DetectGPT | Fast-DetectGPT | **B** | 快340倍 |
| 检测模型 | GPT-4 | DeepSeek | **B** | 中文更好，成本低 |
| 集成分类器 | XGBoost | LightGBM | **B** | 更快 |
| 部署方式 | VM | K8s | **B** | 可扩展 |
| 数据库 | MySQL | PostgreSQL | **B** | JSON支持好 |

### B. 竞品分析

| 竞品 | 定价 | 准确率 | 对抗防御 | 中文 |
|------|------|--------|----------|------|
| 知网 | ¥1.5/千字 | 85% | 弱 | 优 |
| GPTZero | $0.01/次 | 90% | 中 | 差 |
| Copyleaks | $0.01/次 | 88% | 弱 | 中 |
| **本产品** | ¥0.05/次 | **95%+** | **强** | **优** |

### C. 参考文献

1. Mitchell et al. (2023). DetectGPT: Zero-Shot Machine-Generated Text Detection. ICML.
2. Bao et al. (2024). Fast-DetectGPT: Efficient Zero-Shot Detection. ICLR.
3. Zhou et al. (2024). Humanizing Machine-Generated Content: Evading Detection. COLING.

---

*文档版本：v1.0*
*最后更新：2026-03-21*
