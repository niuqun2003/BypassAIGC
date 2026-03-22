# AIGC 检测 MVP 交付文档

**版本：** 1.0.0-mvp
**交付日期：** 2026-03-22
**状态：** 已交付，可用于本地验证

---

## 一、产品定位

本 MVP 是一个**学术文本 AIGC 风险自查工具**，定位为辅助判断工具，不作为最终裁定依据。

| 是 | 不是 |
|----|------|
| 改写后的自查参考 | 知网 / Turnitin 的替代品 |
| 章节级 + 片段级风险筛查 | 学术不端最终判定系统 |
| 报告式输出，可读可解释 | 高精度 AI 溯源鉴定工具 |
| 支持降低知网检测频次（节省费用） | 保证能通过任何第三方检测 |

---

## 二、交付内容

### 2.1 新增文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `package/backend/app/services/detection_service.py` | 后端服务 | 检测核心逻辑（全量重写） |
| `package/backend/app/routes/detection.py` | 后端路由 | `/api/detection/analyze` 端点 |
| `package/backend/tests/test_detection_service.py` | 测试 | 13 个覆盖契约/解析/打分/解释/降级路径的测试 |
| `package/frontend/src/components/DetectionReport.jsx` | 前端组件 | CNKI 风格报告组件（全量重写） |
| `docs/detection/dataset_notes.md` | 文档 | 数据集策略、阈值校准说明、已知限制 |
| `docs/detection/mvp-delivery.md` | 文档 | 本文档 |

### 2.2 修改文件

| 文件 | 变更内容 |
|------|---------|
| `package/backend/app/schemas.py` | 新增 6 个 Detection Pydantic 模型 |
| `package/frontend/src/api/index.js` | 新增 `detectionAPI.analyze()` |
| `package/frontend/src/pages/SessionDetailPage.jsx` | Tab 4 接入 DetectionReport，未完成会话时显示占位提示 |
| `README.md` | 新增 AIGC 风险筛查功能说明章节 |

### 2.3 Commit 记录

```
f655526  docs: add detection calibration notes and readme section
8446c62  feat: integrate detection report into session detail tab
44458a0  feat: upgrade detection report ui to mvp layout
c6fc0fc  feat: implement aigc detection mvp contract (tasks 1-5)
5a7c08c  feat: 集成 AIGC 检测模块（文体特征 + LLM 双层检测）
```

---

## 三、技术架构

### 3.1 检测流水线

```
用户文本输入
     │
     ├─► Layer 1：文体特征（本地，零成本）
     │       ├── 突发度（句长变异系数）
     │       ├── 词汇多样性（MATTR TTR）
     │       ├── 连接词密度（中英双语词表）
     │       ├── 句式单一性（AI 模板正则）
     │       └── 段落长度方差
     │
     ├─► 章节解析（split_document_sections）
     │       ├── 中文序号标题：一、二、（一）
     │       ├── 数字标题：1. 1.1 2.
     │       ├── 英文章节：Chapter / Section / Introduction 等
     │       └── 无标题回退：每 3 段合为伪章节
     │
     ├─► Layer 2：LLM 评分（可选，use_llm=False 时跳过）
     │       └── 调用已配置的 POLISH/DETECT API
     │           失败时静默降级，不影响报告输出
     │
     └─► 综合打分
             ├── 仅文体：文体分 × 100%，置信度=medium
             └── 文体+LLM：文体 35% + LLM 65%，置信度=high
```

### 3.2 风险等级映射

| 等级 | 分数阈值 | 颜色 | 含义 |
|------|---------|------|------|
| `significant`（显著疑似） | ≥ 65 | 红 | 建议优先人工修改 |
| `suspected`（疑似） | ≥ 40 | 橙 | 建议复核 |
| `unmarked`（未标记） | < 40 | 绿 | 低风险 |

> 阈值集中定义于 `detection_service.py` 的 `DEFAULT_HIGH_THRESHOLD` / `DEFAULT_MEDIUM_THRESHOLD`，便于后期校准。

---

## 四、API 契约

### 请求

```
POST /api/detection/analyze?card_key=<key>
Content-Type: application/json
```

```json
{
  "text": "待检测文本（10-100000字）",
  "use_llm": true,
  "detect_model": null,
  "detect_api_key": null,
  "detect_base_url": null
}
```

### 响应结构

```json
{
  "document_score": 72,
  "document_tier": "significant",
  "document_tier_cn": "显著疑似",
  "confidence": "high",

  "sections": [
    {
      "title": "一、引言",
      "char_count": 320,
      "score": 78,
      "tier": "significant",
      "tier_cn": "显著疑似",
      "text_preview": "本研究旨在探讨..."
    }
  ],

  "fragments": [
    {
      "text": "此外，实验结果表明该方法具有显著优势...",
      "score": 81,
      "tier": "significant",
      "section_id": 0,
      "explanation": {
        "summary": "检测到以下风险信号：连接词密度过高；句式单一化模板",
        "signal_keys": ["connector_density", "sentence_uniformity"],
        "evidence_labels": ["连接词密度过高", "句式单一化模板"]
      }
    }
  ],

  "explanations": [
    {
      "signal_key": "connector_density",
      "label": "连接词密度过高",
      "summary": "检测到以下风险信号：连接词密度过高"
    }
  ],

  "report_metadata": {
    "char_count": 850,
    "flagged_char_count": 520,
    "processing_time_ms": 120,
    "llm_used": true,
    "llm_available": true,
    "model_name": "gemini-2.5-pro"
  },

  "stylometric": {
    "ai_score": 0.62,
    "features": {
      "burstiness":          {"value": 0.21, "risk": 0.70, "label": "突发度（低=AI）"},
      "type_token_ratio":    {"value": 0.58, "risk": 0.30, "label": "词汇多样性（低=AI）"},
      "connector_density":   {"value": 6.5,  "risk": 0.81, "label": "连接词密度（高=AI）"},
      "sentence_uniformity": {"value": 0.44, "risk": 0.66, "label": "句式单一性（高=AI）"},
      "para_length_var":     {"value": 0.18, "risk": 0.78, "label": "段落长度方差（低=AI）"}
    },
    "stats": {"sentence_count": 12, "paragraph_count": 4, "token_count": 380, "char_count": 850}
  },

  "llm": {
    "available": true,
    "aigc_probability": 80,
    "confidence": "high",
    "signals": ["句式规整，缺乏个人视角", "连接词使用程式化"]
  },

  "risk_legend": {
    "significant": {"label": "显著疑似", "threshold": 65, "color": "red"},
    "suspected":   {"label": "疑似",     "threshold": 40, "color": "orange"},
    "unmarked":    {"label": "未标记",   "threshold": 0,  "color": "green"}
  }
}
```

> **MVP 说明：** `fragments[].text` 为片段完整原文。Inline 高亮所需的 `start/end` 字符偏移量为 v2 功能，本版本不实现。

---

## 五、前端报告区块

会话详情页 → Tab 4「AIGC 检测」包含以下区块（按顺序）：

| # | 区块 | 默认展开 | 说明 |
|---|------|---------|------|
| ① | 总览卡片 | 是 | 得分圆环 + 风险等级 + 字数统计 + LLM 信号 |
| ② | 风险片段证据 | 是 | 按分数降序，最多展示前 10 个片段，含解释 |
| ③ | 章节风险分布 | 否 | 各章节标题 + 分数 + 等级标签 |
| ④ | 文体特征分析 | 是 | 5 个特征进度条 + 原始值 |
| ⑤ | 信号解释说明 | 否 | 触发信号的可审计解释列表 |
| ⑥ | 风险图例 | — | 三级图例说明（常驻底部） |

---

## 六、本地验证步骤

### 后端测试

```bash
source package/venv/bin/activate
PYTHONPATH=package/backend pytest package/backend/tests/test_detection_service.py -v
# 期望：13 passed

PYTHONPATH=package/backend pytest package/backend/tests/ -q
# 期望：22 passed
```

### 前端构建

```bash
cd package/frontend && npm run build
# 期望：✓ built，零报错
```

### 接口手动验证

```bash
# 启动后端
uvicorn app.main:app --reload --app-dir package/backend --port 8000

# 调用接口（替换 card_key）
curl -X POST "http://localhost:8000/api/detection/analyze?card_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "一、引言\n本研究旨在探讨深度学习的应用。此外，实验结果表明该方法具有显著优势。综上所述，本文贡献如下。\n\n二、方法\n本文采用Transformer架构，结合注意力机制。值得注意的是，该模型取得了领先性能。",
    "use_llm": false
  }'
```

期望响应包含：`document_score`、`sections`（2个章节）、`fragments`、`explanations`、`report_metadata.llm_used = false`。

---

## 七、配置说明

### 可选的检测专用 API 配置（`.env`）

```properties
# 不填则自动复用 POLISH_* 配置
DETECT_MODEL=
DETECT_API_KEY=
DETECT_BASE_URL=
```

### 阈值调整（`detection_service.py`）

```python
# 集中配置，改这两个值即可重新校准
DEFAULT_HIGH_THRESHOLD = 65    # significant 起始分
DEFAULT_MEDIUM_THRESHOLD = 40  # suspected 起始分
```

---

## 八、已知限制

| 限制 | 说明 |
|------|------|
| 短文本可信度低 | < 200 字时特征统计不稳定，结果仅供参考 |
| 高规范学术文本误报 | 本身正式严谨的学术写作与 AI 风格重叠，存在误报 |
| 双语校准未分离 | 中英文使用统一阈值，分语言校准为后期工作 |
| 轻度编辑 AI 文本召回率低 | 人工修改后的 AI 文本是最难区分的类别 |
| Inline 高亮未实现 | fragments 无 start/end 偏移量，v2 功能 |
| LLM 评分非必须 | 无 API 配置时自动降级为纯文体特征模式 |

---

## 九、后续迭代路径

| 优先级 | 工作项 |
|--------|--------|
| P1 | 收集种子数据集（200-500 条双语样本），校准阈值 |
| P1 | 分语言（中/英）分别校准特征权重和阈值 |
| P2 | 添加 `start/end` span 偏移量，实现前端 inline 高亮 |
| P2 | 引入 Fast-DetectGPT 困惑度/突发度计算（替代当前 LLM 评分） |
| P3 | 轻量融合模型（XGBoost/LightGBM）校准，替换线性加权 |
| P3 | HTML 报告导出功能 |
