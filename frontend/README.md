# 前端 — 月蚀议事厅（十人狼人杀）

React 18 + Vite + TypeScript + React Router + Zustand + **Tailwind CSS**。

## 设计系统

完整规范见 [`DESIGN.md`](./DESIGN.md)。

| 项 | 说明 |
|----|------|
| 主题 | 深色「月蚀议事厅」，OKLCH design tokens |
| 字体 | ZCOOL XiaoWei（叙事标题）+ Noto Sans SC（界面）+ JetBrains Mono（数据） |
| 组件 | `src/components/ui/*` 轻量 UI；`src/components/game/*` 对局专用 |
| 图标 | `lucide-react` |

## 页面

| 路由 | 说明 |
|------|------|
| `/` | 大厅 — 沉浸入口、昵称、规则折叠 |
| `/game/:gameId` | 对局 — 圆桌座位环、阶段条、公屏时间线、操作坞 |
| `/replay/:gameId` | 复盘 — `GET /api/games/:id/replay`（公屏 + 身份 + LLM 追溯） |

## 开发

```bash
npm install
npm run dev
```

默认 http://localhost:5173 。API 与 WebSocket 经 Vite 代理到 `localhost:8000`。

```bash
npm run build   # tsc + vite build
npm test        # vitest（若有）
```

## 目录

```
src/
├── main.tsx
├── App.tsx                 # 路由 + AppShell
├── index.css               # Tailwind + OKLCH tokens
├── pages/                  # Lobby / Game / Replay
├── components/
│   ├── layout/             # AppShell, PageState
│   ├── game/               # SeatRing, PhaseBar, PublicLog, ActionDock…
│   └── ui/                 # Button, Badge, Input, Tabs, Collapse
├── stores/gameStore.ts     # Zustand（勿改 WS 契约）
├── hooks/useGameWebSocket.ts
├── types/game.ts
├── api/client.ts
├── lib/cn.ts, labels.ts, replayMapper.ts
└── types/replay.ts
```

## 与后端联调

- REST：`/api` 代理到后端根路径；WS：`/ws` 代理。
- 复盘：`fetchGameReplay` → `GET /games/{id}/replay`（对局须在服务端内存中，重启后丢失见 `../前后端待办.md`）。
