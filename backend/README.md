# 后端 — 十人狼人杀

FastAPI + WebSocket 游戏服务端。支持 **MCP / CLI / Skills / OpenClaw** 多种接入方式。

## 快速开始

### Docker（推荐）

在项目根目录 `0523/`：

```bash
cp backend/.env.example backend/.env   # 填入 LLM Key
docker compose up --build werewolf-backend
```

- API：<http://localhost:8000>
- 内置人格/策略：`backend/data/`
- 用户库持久化：`backend/data/user_libraries/`（compose 挂载到容器 `/app/data`）

### 本地 uvicorn

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"       # 或 pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## 目录

```
app/
├── main.py           # FastAPI 入口
├── config.py         # 环境变量
├── api/              # REST + WebSocket 路由
├── models/           # Pydantic 数据模型
├── services/         # Game Loop、视野过滤
├── game/             # 规则引擎（纯逻辑）
├── llm/              # Qwen 客户端 + Pipeline
├── ai/               # 人格、策略库、信念、记忆、编排
├── mcp/              # MCP Server (Model Context Protocol)
│   ├── server.py     #   FastMCP 实例 + 8 个 Tool 定义
│   └── routes.py     #   SSE 模式 REST API
├── cli/              # Native CLI (Click)
│   └── main.py       #   werewolf 命令行入口
└── skills/           # Skills 插件系统
    ├── base.py       #   BaseSkill 抽象基类
    ├── registry.py   #   SkillRegistry 注册表
    ├── builtin.py    #   6 个内置 Skill
    ├── routes.py     #   Skills REST API
    ├── openclaw.py   #   OpenClaw Adapter
    └── openclaw_routes.py  # OpenClaw REST API
data/
├── personalities.json          # 内置 default 人格库
├── strategies/                 # 内置 default 策略（按身份 JSON）
└── user_libraries/             # 用户创建的人格库 / 策略库（JSON 文件）
    ├── personalities/
    └── strategies/
openclaw_config.yaml  # OpenClaw Agent 配置文件
```

## Qwen API 配置（Phase 3）

使用 **阿里云 DashScope OpenAI 兼容模式**（`httpx` 直连，无需额外 SDK）：

| 变量 | 说明 | 默认 |
|------|------|------|
| `QWEN_API_KEY` | 通义千问 API Key（推荐） | 空 |
| `DASHSCOPE_API_KEY` | 与上二选一 | 空 |
| `QWEN_MODEL` | 模型名 | `qwen-turbo`（开发省成本） |
| `QWEN_BASE_URL` | 兼容端点 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_TIMEOUT_SECONDS` | 单次请求超时 | `25` |
| `LLM_SPEECH_MAX_CHARS` | 发言硬上限字数 | `350` |

### 配置步骤

1. 复制 `cp .env.example .env`
2. 在 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) 创建 API Key
3. 写入 `.env`：`QWEN_API_KEY=sk-xxx`
4. 重启 `uvicorn app.main:app --reload`

### 无 Key 降级

- 未配置 `QWEN_API_KEY` / `DASHSCOPE_API_KEY` 时，**自动使用 Phase 2 Mock AI**（`auto_player`）
- **CI 与单元测试不依赖外网**；`pytest` 默认全部 Mock 通过
- 可选真实调用：`pytest tests/test_llm_integration.py -m integration`（需 Key）

### LLM Pipeline 流程

```
1. select_strategy  — 按身份从策略库选一条，写入 strategy_id + llm_traces
2. decide_action    — 刀/验/救毒/守/投票等 JSON 决策
3. generate_speech  — 白天发言 80～350 字中文
```

每次调用强制注入：人格块、StateView 合法信息、策略史、公开承诺史。

预言家验人等私域结果经 `PRIVATE_MESSAGE` 推送（不进公屏）。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/games` | 创建对局 |
| GET | `/games/{id}` | 对局摘要 |
| GET | `/games/{id}/replay` | 局后复盘（身份、公屏、LLM 追溯、私域） |
| WS | `/ws/games/{id}` | 实时对局事件 |
| GET | `/skills/` | 列出所有 Skill |
| GET | `/skills/{name}` | Skill 详情 |
| POST | `/skills/{name}/execute` | 执行 Skill |
| GET | `/mcp/tools` | 列出 MCP Tool |
| GET | `/mcp/health` | MCP 健康检查 |
| GET | `/openclaw/config` | OpenClaw Tool 定义 |
| POST | `/openclaw/execute` | 执行 OpenClaw Tool |
| GET | `/openclaw/health` | OpenClaw 健康检查 |

详见 [开发流程.md §6](../开发流程.md#6-api-设计概要)。

---

## Native CLI

基于 `click` 构建的命令行工具，安装后可直接使用 `werewolf` 命令：

```bash
werewolf --help
```

| 命令 | 功能 |
|------|------|
| `werewolf create --name 玩家` | 创建新对局 |
| `werewolf list` | 列出活跃对局 |
| `werewolf status <game_id>` | 查看对局状态 |
| `werewolf view <game_id> <seat>` | 查看玩家视野 |
| `werewolf speech <game_id> <seat> <text>` | 提交发言 |
| `werewolf vote <game_id> <seat> <target>` | 提交投票 |
| `werewolf log <game_id>` | 查看公共日志 |
| `werewolf simulate --seed 42` | 模拟对局 |
| `werewolf serve --port 8000` | 启动 FastAPI 服务 |
| `werewolf mcp` | 启动 MCP Server (stdio) |

---

## MCP Server (Model Context Protocol)

将狼人杀后端暴露为 MCP Tools，供 Claude Desktop 等 LLM Host 调用。

### 运行方式

**方式一：stdio 模式**（推荐，用于 Claude Desktop 等 Host）

```bash
werewolf mcp
# 或
werewolf-mcp
```

**方式二：SSE 模式**（跟随 FastAPI 一同启动）

```bash
uvicorn app.main:app --port 8000
# 访问 http://localhost:8000/mcp/tools 查看 Tool 列表
```

### 可用 Tools

| Tool | 说明 |
|------|------|
| `create_game` | 创建新对局，返回 game_id/player_token/role |
| `get_game_summary` | 获取对局摘要：阶段、存活、日志 |
| `list_games` | 列出所有活跃对局 |
| `get_player_view` | 获取指定玩家的合法视野 |
| `submit_speech` | 提交发言（仅人类玩家） |
| `submit_vote` | 提交放逐投票 |
| `get_public_log` | 获取公共日志 |
| `health_check` | 健康检查 |

### Claude Desktop 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "werewolf": {
      "command": "werewolf-mcp"
    }
  }
}
```

---

## Skills 插件系统

基于 `BaseSkill` 抽象基类的插件化 Skill 系统，支持注册、发现、远程调用。

### 内置 Skill

| Skill | 分类 | 说明 |
|-------|------|------|
| `create_game` | game | 创建对局 |
| `get_game_state` | game | 获取对局状态 |
| `list_games` | game | 列出活跃对局 |
| `submit_vote` | game | 提交投票 |
| `get_public_log` | game | 获取公共日志 |
| `health_check` | system | 健康检查 |

### REST API

```bash
# 列出所有 Skill
curl http://localhost:8000/skills/

# 获取 Skill 详情
curl http://localhost:8000/skills/create_game

# 执行 Skill
curl -X POST http://localhost:8000/skills/create_game/execute \
  -H "Content-Type: application/json" \
  -d '{"player_name": "测试"}'
```

### 自定义 Skill

继承 `BaseSkill` 并实现 `execute` 方法即可：

```python
from app.skills.base import BaseSkill, SkillContext, SkillResult

class MySkill(BaseSkill):
    name = "my_skill"
    description = "自定义 Skill"
    category = "custom"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        # 业务逻辑
        return SkillResult(success=True, data={"result": "ok"})
```

自动发现：将自定义 Skill 放入 `app/skills/builtin/` 包下，启动时自动注册。

---

## OpenClaw 集成

将狼人杀后端暴露为 OpenClaw Agent 的 Tool Provider。

### REST API

```bash
# 获取 OpenClaw Tool 定义列表
curl http://localhost:8000/openclaw/config

# 执行 OpenClaw Tool
curl -X POST http://localhost:8000/openclaw/execute \
  -H "Content-Type: application/json" \
  -d '{"name": "create_game", "arguments": {"player_name": "测试"}}'

# 健康检查
curl http://localhost:8000/openclaw/health
```

### Agent 配置

`openclaw_config.yaml` 可直接嵌入 OpenClaw Agent 配置：

```yaml
name: werewolf
version: "0.1.0"
description: "十人狼人杀 AI 对局服务"
base_url: "http://localhost:8000"
tools:
  - name: create_game
    endpoint: /openclaw/execute
    method: POST
```

---

## 测试

```bash
pytest tests -v
```

## Phase 2 手动验收

1. **启动后端**（端口 8000）：
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. **启动前端**（端口 5173，代理 `/api` 与 `/ws`）：
   ```bash
   cd ../frontend
   pnpm install   # 首次
   pnpm dev
   ```

3. 浏览器打开 `http://localhost:5173` → 输入昵称 → **开始新局**

4. 自动跳转对局页，WebSocket 应显示 **已连接**，并收到：
   - `GAME_STARTED`（你的座位与身份）
   - `PHASE_CHANGED`（夜晚/白天阶段切换）
   - `PUBLIC_LOG`（系统消息与 AI 发言）
   - Mock AI 自动推进夜晚与白天流程

5. 轮到你时：
   - **发言阶段**：输入框 + 倒计时 → 提交或跳过
   - **投票阶段**：选择目标 → 确认投票
   - **夜晚神职/狼人**：私域操作面板（不进公屏）

6. 开发环境可缩短发言时间：`.env` 中设置 `GAME_SPEECH_MAX_SECONDS=10`

## WebSocket 事件流（简）

```
客户端连接 ?token=...
  ← CONNECTED
  ← GAME_STARTED
  ← PHASE_CHANGED / STATE_SNAPSHOT
  → (GameLoop 启动，Mock AI 自动提交 AI 行动)

白天发言：
  ← SPEAK_TURN_START { seat, deadline_ts, is_you }
  → SUBMIT_SPEECH / SKIP_SPEECH（仅 is_you）
  ← SPEAK_TURN_END / PUBLIC_LOG
  ← PHASE_CHANGED (day_vote)

投票：
  ← VOTE_STARTED
  → SUBMIT_VOTE { target_seat | null }
  ← VOTE_RESULT / PUBLIC_LOG

夜晚（人类有神/狼/预）：
  ← NIGHT_ACTION_REQUEST
  → SUBMIT_NIGHT_ACTION
  ← PHASE_CHANGED

私域（仅目标座位）：
  ← PRIVATE_MESSAGE { channel, content, ... }   # seer_result 等

死后观战（基础）：
  ← SPECTATOR_MODE

结束：
  ← GAME_END { winner, replay_url }
```

## Phase 4 待办（复盘 UI）

- 三级复盘视图：时间线 / 单玩家 / 单 AI 思考链（消费 `llm_traces`、`belief_by_seat`）
- 死后观战 UI 对接 `SPECTATOR_MODE` 与私域历史
- 玩家私域操作面板完善
- 发言时长与 30 分钟局时优化
