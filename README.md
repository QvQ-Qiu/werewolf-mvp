# 十人狼人杀 MVP

**1 人 + 9 AI** 的预女猎守狼人杀。你在局中推理，其余九席由 AI 扮演——看它们互撕、投票、夜里私聊，目标约 **30 分钟一局**。

仓库：[github.com/QvQ-Qiu/werewolf-mvp](https://github.com/QvQ-Qiu/werewolf-mvp)

## 特性

| 能力 | 说明 |
|------|------|
| 固定板子 | 3 狼 · 预女猎守 · 4 民 · **无警长** |
| 规则引擎 | Python 纯逻辑，AI 只能通过合法 Action 影响局面 |
| 实时对局 | WebSocket 推送阶段、公屏、投票与技能结算 |
| AI 编排 | 策略库 → 行动 → 发言 Pipeline；人格 / 信念 / 记忆压缩 |
| 人格与策略库 | 内置模板 + 用户自定义（大厅可编辑） |
| 复盘 | 公屏时间线 + 身份揭示 + LLM 调用追溯 |
| 多 LLM | Coze（默认）、火山方舟、通义、OpenAI 兼容、本地 vLLM |
| 扩展接入 | MCP · CLI · Skills · OpenClaw（见 [backend/README.md](./backend/README.md)） |

**MVP 边界**：无语音实装、无白天插话、无警长流、玩家狼刀不计入狼队票。产品细节见 [最小mvp.md](./最小mvp.md)。

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | React 18 · Vite · TypeScript · React Router · Zustand · Tailwind |
| 后端 | Python 3.11+ · FastAPI · WebSocket · Pydantic |
| 持久化 | 内存对局 + JSON 复盘 / 用户库落盘 |
| 部署 | Docker Compose（可选挂载前端 dev profile） |

架构与阶段规划见 [开发流程.md](./开发流程.md)。

## 环境要求

- **Node.js** 18+（前端，`npm` 或 `pnpm`）
- **Python** 3.11+（后端）
- 至少一种 **LLM API Key**（见 `backend/.env.example`）

## 快速开始

### 方式一：Docker（仅后端，推荐先试玩 API）

在项目根目录：

```bash
cp backend/.env.example backend/.env   # 填入 COZE_INTEGRATION_API_KEY 等
docker compose up --build werewolf-backend
```

- API / 健康检查：<http://localhost:8000> · <http://localhost:8000/health>
- 若构建时挂载了前端 `dist`，同一端口可访问静态页面

前端开发模式（Vite 热更新，需本机已装 Docker）：

```bash
docker compose --profile dev up werewolf-frontend-dev
```

### 方式二：本地开发（前后端分离）

**1. 后端**

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env          # 配置 LLM，见下方说明
uvicorn app.main:app --reload --port 8000
```

**2. 前端**（另开终端）

```bash
cd frontend
npm install    # 或 pnpm install
npm run dev    # 或 pnpm dev
```

| 服务 | 地址 |
|------|------|
| 前端 | <http://localhost:5173> |
| 后端 API | <http://localhost:8000> |
| API 文档 | <http://localhost:8000/docs> |

前端通过 Vite 代理访问后端；`CORS_ORIGINS` 默认包含 `http://localhost:5173`。

### LLM 配置（`backend/.env`）

复制 `backend/.env.example` 后，**至少配置一种**提供方（优先级见文件内注释）：

| 变量 | 用途 |
|------|------|
| `COZE_INTEGRATION_API_KEY` | Coze 集成（推荐默认） |
| `ARK_API_KEY` | 火山方舟 |
| `QWEN_API_KEY` | 通义千问 / DashScope |
| `OPENAI_API_KEY` | OpenAI 或任意兼容端点 |
| `LLM_BASE_URL` + `LLM_MODEL` | 本地 vLLM 等 OpenAI 兼容服务 |

对局节奏相关：`GAME_SPEECH_MAX_SECONDS`、`LLM_SPEECH_MAX_CHARS` 等见 `.env.example`。

## 常用命令

```bash
# 后端测试
cd backend && pytest

# 前端测试与构建
cd frontend && npm test && npm run build

# CLI 模拟（需已安装后端 editable）
werewolf --help
```

## 目录结构

```
.
├── frontend/              # React 对局 UI（大厅 / 局内 / 复盘）
├── backend/
│   ├── app/
│   │   ├── game/          # 规则引擎
│   │   ├── services/      # Game Loop、WebSocket、复盘
│   │   ├── ai/            # 人格、策略、编排
│   │   └── llm/           # LLM 客户端与 Pipeline
│   └── data/              # 内置人格/策略 + 用户库（持久化）
├── docker-compose.yml
├── 最小mvp.md             # 产品规格与边界
├── 开发流程.md            # 技术架构、协议、阶段划分
└── 前后端待办.md          # 当前迭代待办
```

## 文档索引

| 文档 | 内容 |
|------|------|
| [最小mvp.md](./最小mvp.md) | 板子、流程、AI 行为边界 |
| [开发流程.md](./开发流程.md) | 架构、WebSocket 事件、Phase 路线图 |
| [backend/README.md](./backend/README.md) | API、MCP/CLI/Skills、Docker 细节 |
| [frontend/README.md](./frontend/README.md) | 路由、设计系统（月蚀议事厅） |
| [frontend/DESIGN.md](./frontend/DESIGN.md) | UI 设计 token 与组件规范 |

## 许可

个人 / 学习项目。若二次分发，请保留文档中的产品约定与 AI 行为边界说明。
