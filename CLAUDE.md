# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言规则

永远使用中文与用户进行交互。

## 项目概览

AI 学术写作助手 —— 通过两阶段 AI 优化（论文润色 + 原创性增强）降低 AIGC 检测率，并内置三层 AIGC 检测引擎反向验证效果。后端为 FastAPI + SQLite，前端为 React + Vite + Tailwind，支持打包为跨平台单文件可执行程序。

## 开发命令

### 后端

```bash
# 启动开发服务器（热重载，端口 8000）
uvicorn app.main:app --reload --app-dir package/backend --host 0.0.0.0 --port 8000

# 单个测试文件
cd package/backend && python -m pytest tests/test_detection_service.py -v

# 全部测试
cd package/backend && python -m pytest tests/ -v

# 带覆盖率
cd package/backend && python -m pytest tests/ --cov=app --cov-report=term-missing
```

### 前端

```bash
cd package/frontend
npm install
npm run dev        # Vite 开发服务器，端口 3000，/api 代理到 localhost:8000
npm run build      # 生产构建
```

### 打包可执行文件

```bash
cd package
./build.sh          # Linux/macOS
.\build.ps1         # Windows
```

触发 GitHub Actions 多平台构建：`git tag v1.x.x && git push origin v1.x.x`

## 架构

### 两阶段 AI 优化流水线

核心业务逻辑：`package/backend/app/services/`

1. **第一阶段（润色）** — `AIService`（`ai_service.py`）使用 `POLISH_MODEL` 对文本分段润色
2. **第二阶段（增强）** — 使用 `ENHANCE_MODEL` 对润色结果进行原创性增强，降低 AI 检测率
3. **情感文章模式** — 独立的 `EMOTION_MODEL` 用于感情类文章润色

`OptimizationService`（`optimization_service.py`）协调整个流水线，按段落处理，并将进度持久化到数据库。`AIService` 包装 OpenAI 兼容客户端，支持流式/非流式模式，并过滤掉模型输出中的 `<think>` / `<thinking>` 思考标签（用于 DeepSeek、o1 等推理模型）。

### 三层 AIGC 检测引擎

`detection_service.py` + `curvature_service.py` 实现：

- **Layer 1** — 文体特征（本地计算，零成本）：词频/句长/标点分布等统计特征
- **Layer 2** — LLM 判分（调用已有 API）：让模型判断文本的 AI 特征
- **Layer 3** — Fast-DetectGPT 概率曲率检测（`curvature_service.py`）：通过 logprobs + top_logprobs 估算条件概率曲率，AI 文本趋向正曲率，人类文本趋向零曲率

前端 `DetectionReport.jsx` 展示检测报告，集成在会话详情的 Tab 中。

### 并发与队列

`concurrency_manager`（`concurrency.py`）控制同时运行的用户会话数（`MAX_CONCURRENT_USERS`），超出则排队等待。`stream_manager`（`stream_manager.py`）管理 SSE 流式推送。

### 卡密认证

用户通过卡密（card_key）访问，存储在前端 `localStorage`，每次请求作为查询参数传递。管理后台使用 JWT（`/api/admin/login`），通过 `utils/auth.py` 验证。

### 配置热更新

系统配置（模型名称、并发数、流式开关等）可在管理后台实时修改并写回 `.env`，无需重启。`app/config.py` 的 `Settings` 类（pydantic-settings）负责加载，`reload_settings()` 负责热更新。

`.env` 文件路径通过 `APP_BASE_DIR` 环境变量注入（打包模式）或自动推断（开发模式），统一由 `get_exe_dir()` 解析。

### 关键路由

- `routes/optimization.py` — 文本优化主流程（`/api/optimize/*`）
- `routes/detection.py` — AIGC 检测（`/api/detection/analyze`）
- `routes/admin.py` — 管理后台（卡密、用户、配置、会话监控）
- `routes/export.py` — 导出功能
- `routes/upload.py` — 文件上传
- `routes/prompts.py` — 提示词管理

### 前端结构

- `pages/WelcomePage.jsx` — 卡密登录
- `pages/WorkspacePage.jsx` — 主编辑器（输入/输出/对比视图）
- `pages/SessionDetailPage.jsx` — 会话详情（含检测报告 Tab）
- `pages/AdminDashboard.jsx` — 管理后台入口，内含 `components/` 下的各功能面板
- `src/api/index.js` — 所有 Axios 请求集中在此，统一使用 `/api` 前缀

### 数据库

SQLite（`ai_polish.db`），通过 SQLAlchemy 管理。主要模型：`User`、`OptimizationSession`、`OptimizationSegment`、`SessionHistory`、`ChangeLog`、`CustomPrompt`。`OptimizationSession` 记录每个段落的处理进度，支持断点续传（`current_position` + `failed_segment_index`）。

## 多模型配置说明

`.env` 中每个阶段可独立配置模型和 API：

| 前缀 | 用途 |
|------|------|
| `POLISH_*` | 第一阶段润色模型 |
| `ENHANCE_*` | 第二阶段增强模型 |
| `EMOTION_*` | 情感文章润色模型（可选） |
| `COMPRESSION_*` | 会话历史压缩模型 |
| `DETECT_*` | AIGC 检测 Layer 2 模型（不填则回退到 POLISH_*） |
| `CURVATURE_*` | 曲率检测 Layer 3 模型（不填则逐级回退） |

## 访问地址

| 地址 | 用途 |
|------|------|
| http://localhost:8000 | 用户界面 |
| http://localhost:8000/admin | 管理后台 |
| http://localhost:8000/docs | FastAPI Swagger 文档 |
