# 十人狼人杀 MVP

1 人 + 9 AI 的预女猎守狼人杀 MVP。详见 [最小mvp.md](./最小mvp.md) 与 [开发流程.md](./开发流程.md)。

## 目录结构

```
0523/
├── 最小mvp.md      # 产品需求
├── 开发流程.md      # 开发流程与技术规格
├── frontend/       # React + Vite + TypeScript
└── backend/        # Python FastAPI
```

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cp .env.example .env     # 填入 OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- 健康检查：http://localhost:8000/health

## 开发阶段

参见 [开发流程.md §4](./开发流程.md#4-开发阶段划分)。当前为 **Phase 0**：项目骨架。
