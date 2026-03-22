# AIGC内容检测算法调研

> 调研时间：2026-03-21
> 目标：知网检测系统对抗研究 + 自建检测系统

---

## 一、知网AIGC检测原理分析

### 核心检测指标

| 指标 | 说明 | AI特征 |
|------|------|--------|
| **句式特征** | 句子结构模式 | 偏好"总分总"结构，句式单一 |
| **术语密度** | 专业名词占比 | 异常偏低，通用词多 |
| **逻辑连贯性** | 段落衔接 | 缺乏过渡连接词，机械堆砌 |

### 检测准确率
- GPT-3.5 等旧模型：约 89.7%
- 新模型（GPT-4, Claude）：准确率下降明显

---

## 二、学术前沿：检测算法

### 2.1 概率曲率法（DetectGPT）

**论文**：*Zero-Shot Machine-Generated Text Detection using Probability Curvature* (ICML 2023)

**核心原理**：
- AI生成文本在对数概率曲面上呈现**负曲率**特性
- 通过计算文本在生成模型下的概率分布曲率来判断
- **无需训练**，零样本检测

**性能**：AUROC 0.95+

### 2.2 快速检测（Fast-DetectGPT）

**论文**：*Efficient Zero-Shot Detection of Machine-Generated Text via Conditional Probability Curvature* (ICLR 2024)

**改进**：
- 用**条件概率采样**替代概率扰动
- 速度提升 **340倍**
- 准确率提升 **75%**

### 2.3 文体学特征

知网等商业系统采用的多维特征：
- 词频统计
- 句长分布
- 困惑度（Perplexity）
- 突发度（Burstiness）

---

## 三、对抗攻击方法

### 3.1 核心论文：Evading AI-Text Detection through Adversarial Attack

**论文信息**：
- 标题：*Humanizing Machine-Generated Content: Evading AI-Text Detection through Adversarial Attack*
- 会议：COLING 2024
- arXiv：2404.01907

**核心发现**：
> ⚠️ **当前检测模型可在 10 秒内被攻破**

**攻击方法**：

| 方法 | 类型 | 说明 |
|------|------|------|
| **同义词替换** | 白盒 | 替换高影响词降低检测置信度 |
| **句法重组** | 黑盒 | 改变句子结构保持语义不变 |
| **扰动注入** | 白盒 | 在关键位置注入小扰动 |
| **改写攻击** | 黑盒 | 使用另一模型改写文本 |

**实验结果**：
- 对 GPTZero 攻击成功率：**95%+**
- 对 DetectGPT 攻击成功率：**90%+**
- 对知网系统：**未公开数据，但方法适用**

### 3.2 实用绕过策略

根据学术论文和实战经验：

1. **人工改写**
   - 加入个人经历和细节
   - 使用口语化表达
   - 加入情绪词和感叹

2. **AI辅助改写**
   - 让 AI 用"口语化"、"非正式"风格重写
   - 指定特定人设（如"初中生"、"老太太"）
   - 分段改写后人工拼接

3. **结构破坏**
   - 打破"总分总"结构
   - 加入跑题内容和絮叨
   - 长短句混搭

4. **术语增强**
   - 手动加入专业术语
   - 引用具体数据和案例
   - 加入时间、地点、人名

---

## 四、开源检测系统

### 4.1 主流开源项目

| 项目 | 技术 | GitHub Stars | 说明 |
|------|------|--------------|------|
| **DetectGPT** | 概率曲率 | 1k+ | 斯坦福大学，零样本 |
| **GPTZero** | 困惑度+突发度 | 3k+ | 商业化+开源版 |
| **GPTSniffer** | RoBERTa | 500+ | 监督学习 |
| **GLTR** | 可视化 | 2k+ | 哈佛大学，可视化工具 |

### 4.2 腾讯云 AIGC 检测 API

**Skill已安装**：
- `tencentcloud-aigc-recog-text` - 文本检测
- `tencentcloud-aigc-recog-image` - 图片检测

**API 调用**：
```python
# 文本检测
TextModeration(Type="TEXT_AIGC", Text="待检测文本")

# 图片检测
ImageModeration(Type="IMAGE_AIGC", ImageUrl="图片URL")
```

---

## 五、自建检测系统路线

### 5.1 技术路线选择

| 路线 | 难度 | 准确率 | 成本 | 适用场景 |
|------|------|--------|------|----------|
| **零样本检测** | 低 | 85-90% | 高（需大模型API） | 快速部署 |
| **监督学习** | 中 | 90-95% | 低 | 大规模应用 |
| **混合方法** | 高 | 95%+ | 中 | 生产环境 |

### 5.2 推荐架构

```
┌─────────────────────────────────────────────┐
│              输入文本                        │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼───┐                 ┌─────▼────┐
│ 概率曲率 │                 │ 文体特征  │
│ (Fast-DetectGPT)│        │ (词频、句长)│
└───┬───┘                 └─────┬────┘
    │                           │
    └─────────────┬─────────────┘
                  │
          ┌───────▼────────┐
          │   集成分类器    │
          │ (XGBoost/LightGBM)│
          └───────┬────────┘
                  │
          ┌───────▼────────┐
          │   输出结果      │
          │ (AI概率 + 置信度)│
          └────────────────┘
```

### 5.3 训练数据构建

**数据来源**：
- HC3 数据集（人类与ChatGPT对比）
- GPT-4 生成样本
- 人类写作样本（维基百科、知乎等）

**数据增强**：
- 改写攻击样本
- 对抗样本注入
- 多模型混合生成

---

## 六、研究建议

### 短期（1-2周）
1. 部署 Fast-DetectGPT 开源版本
2. 对接腾讯云 AIGC 检测 API
3. 收集测试样本（知网检测过的论文）

### 中期（1-2月）
1. 训练自定义检测模型
2. 建立中文语境优化
3. 对抗攻击测试

### 长期（3-6月）
1. 多模型集成
2. 实时更新对抗策略
3. 部署生产环境

---

## 七、产品规划

**核心方案**：[AIGC检测产品方案.md](AIGC检测产品方案.md)

### 产品定位
> **"三重检测 + 对抗防御"**

### 核心优势
- 秒级检测（Fast-DetectGPT）
- 成本低（¥0.01-0.03/次）
- 对抗鲁棒（集成+对抗训练）
- 中文优化

### 技术架构
```
三重检测引擎：
├── 零样本检测（Fast-DetectGPT）
├── 文体特征检测（词频/句法/困惑度）
└── 对抗防御模块（异常检测）
        │
        ▼
    集成分类器（LightGBM）
        │
        ▼
    置信度校准 + 对抗标记
```

---

## 八、论文详细分析

| 论文 | 文件 | 核心贡献 |
|------|------|----------|
| **DetectGPT** | [DetectGPT论文分析.md](DetectGPT论文分析.md) | 发现概率曲率特征，零样本检测 |
| **Fast-DetectGPT** | [Fast-DetectGPT论文分析.md](Fast-DetectGPT论文分析.md) | 快 340 倍，准确率提升 75% |
| **对抗攻击** | [对抗攻击论文分析.md](对抗攻击论文分析.md) | 10 秒攻破检测器，警示脆弱性 |

### 核心论文引用
1. Mitchell et al. (2023). DetectGPT: Zero-Shot Machine-Generated Text Detection using Probability Curvature. ICML.
2. Bao et al. (2024). Fast-DetectGPT: Efficient Zero-Shot Detection via Conditional Probability Curvature. ICLR.
3. Zhou et al. (2024). Humanizing Machine-Generated Content: Evading AI-Text Detection through Adversarial Attack. COLING.

### 开源项目
- DetectGPT: https://github.com/eric-mitchell/detect-gpt
- GPTZero: https://github.com/BurhanUlTayyab/GPTZero
- GLTR: https://github.com/HendrikStrobworeit/GLTR

### 相关资源
- 知网AIGC检测解析: https://blog.csdn.net/CikAiyyds/article/details/146932897
- 智源社区分析: https://hub.baai.ac.cn/view/27571

---

## 八、风险提示

⚠️ **学术诚信警告**
- 本调研仅供技术研究
- 规避检测可能违反学术规范
- 请遵守所在机构的相关规定

⚠️ **检测局限性**
- 所有检测系统都存在误判
- 对抗攻击持续进化
- 检测与生成的"军备竞赛"将持续

---

*文档持续更新中...*
