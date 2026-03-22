# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言规则

永远使用中文与用户进行交互。

## 项目概览

AI 学术写作助手 —— 通过两阶段 AI 优化（论文润色 + 原创性增强）降低 AIGC 检测率。后端为 FastAPI + SQLite，前端为 React + Vite + Tailwind，支持打包为跨平台单文件可执行程序。

## 开发命令

### 后端
```bash
# 启动开发服务器（热重载，端口 8000）
uvicorn app.main:app --reload --app-dir package/backend --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd package/frontend
npm install
npm run dev        # Vite 开发服务器，端口 3000，/api 代理到 localhost:8000
npm run build      # 生产构建
```

### 测试
```bash
# 后端测试（在 package/backend 目录下运行）
cd package/backend
python -m pytest tests/ -v
```

### 打包可执行文件
```bash
cd package
./build.sh          # Linux/macOS
.\build.ps1         # Windows
```

触发 GitHub Actions 构建：`git tag v1.x.x && git push origin v1.x.x`

## 架构

### 两阶段 AI 优化流水线

核心业务逻辑：`package/backend/app/services/`

1. **第一阶段（润色）** — `AIService`（`ai_service.py`）使用 `POLISH_MODEL` 对文本分段润色
2. **第二阶段（增强）** — 使用 `ENHANCE_MODEL` 对润色结果进行原创性增强，降低 AI 检测率
3. **情感文章模式** — 独立的 `EMOTION_MODEL` 用于感情类文章润色

`OptimizationService`（`optimization_service.py`）协调整个流水线，按段落处理，并将进度持久化到数据库。`AIService` 包装 OpenAI 兼容客户端，支持流式/非流式模式，并过滤掉模型输出中的 `<think>` 思考标签。

### 并发与队列

`concurrency_manager`（`concurrency.py`）控制同时运行的用户会话数（`MAX_CONCURRENT_USERS`），超出则排队等待。`stream_manager`（`stream_manager.py`）管理 SSE 流式推送。

### 卡密认证

用户通过卡密（card_key）访问，存储在前端 `localStorage`，每次请求作为查询参数传递。管理后台使用 JWT（`/api/admin/login`），通过 `utils/auth.py` 验证。

### 配置热更新

系统配置（模型名称、并发数、流式开关等）可在管理后台实时修改并写回 `.env`，无需重启。`app/config.py` 的 `Settings` 类负责加载和更新。

### 关键路由
- `routes/optimization.py` — 文本优化主流程（`/api/optimize/*`）
- `routes/admin.py` — 管理后台（卡密、用户、配置、会话监控）
- `routes/export.py` — 导出功能
- `routes/upload.py` — 文件上传
- `routes/prompts.py` — 提示词管理

### 前端结构
- `pages/WelcomePage.jsx` — 卡密登录
- `pages/WorkspacePage.jsx` — 主编辑器（输入/输出/对比视图）
- `pages/AdminDashboard.jsx` — 管理后台入口，内含 `components/` 下的各功能面板
- `src/api/index.js` — 所有 Axios 请求集中在此，统一使用 `/api` 前缀

### 数据库
SQLite（`ai_polish.db`），通过 SQLAlchemy 管理。主要模型：`User`、`OptimizationSession`、`OptimizationSegment`、`SessionHistory`、`ChangeLog`、`CustomPrompt`。

## 访问地址

| 地址 | 用途 |
|------|------|
| http://localhost:8000 | 用户界面 |
| http://localhost:8000/admin | 管理后台 |
| http://localhost:8000/docs | FastAPI Swagger 文档 |
