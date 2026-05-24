# 字体系统 · 市场调研与设计规格

## 1. 市场调研摘要

| 参考 | 字体策略 | 启示 |
|------|----------|------|
| [West of Dead](https://fontsinuse.com/uses/44358/west-of-dead-video-game) | 西部 slab 展示 + 清晰 UI | 标题要有「铭文/通缉令」重量感 |
| [Pentiment](https://www.gamedeveloper.com/design/pentiment-director-explains-how-going-all-in-on-fonts-helped-elevate-the-medieval-detective-rpg-) | 多套定制衬线表达阶层 | 展示字与正文字体分工，建立「叙事声线」 |
| [Kingdom Come II UI](https://www.stormtype.com/custom-fonts/kingdom-come-deliverance-ii) | 哥特展示 + 高可读 UI | 奇幻 UI 仍需克制、可读优先 |
| [Cronos: The New Dawn](https://fontsinuse.com/uses/71834/cronos-the-new-dawn-video-game) | JetBrains Mono 做 HUD | 局号、计时等用等宽增强「系统感」 |

**结论**：在保留中文可读（Noto）前提下，引入 **Cinzel**（西方铭文衬线）与 **Cinzel Decorative**（花饰英文点缀），正文用 **DM Sans** 提升现代游戏 HUD 清晰度；数据/局号用 **JetBrains Mono**。

## 2. 字体角色（四轨）

| 角色 | 字体栈 | 用途 |
|------|--------|------|
| **body** | DM Sans, Noto Sans SC | 正文、按钮、公屏、表单、标签 |
| **display** | Cinzel, Noto Serif SC | 标题、阶段、座位号、结算大字 |
| **flourish** | Cinzel Decorative | 纯英文装饰行（NIGHTFALL / VICTORY） |
| **mono** | JetBrains Mono | 局号、时间戳、倒计时 |

花饰英文 **仅作点缀**（eyebrow 上方一行），不占正文信息承载。

## 3. 分区用字

| 区域 | display | flourish | body | mono |
|------|---------|----------|------|------|
| 全局导航 / 大厅标题 | 品牌名 | GATHERING | 副文案 | — |
| 对局 HUD | 局号、阶段 | ECLIPSE | 连接状态 | 局号片段 |
| 公屏日志 | 座位号 | — | 发言正文 | — |
| 座位列 | 号码 | — | 我/言/亡 | — |
| 操作坞 | 区块标题 | — | 说明、按钮 | 倒计时 |
| 过场（昼夜/身份/结算） | 主标题 | NIGHTFALL 等 | 副文案 | — |
| 技能弹窗 | 技能名 | PRIVATE | 选项 | — |
| 复盘页 | 档案标题 | DOSSIER | 时间线正文 | 时间列 |

## 4. 工程约定

- CSS 变量：`--font-body` / `--font-display` / `--font-flourish` / `--font-mono`
- 工具类：`.text-display` `.text-flourish` `.text-eyebrow` `.font-mono`
- 中文大标题仍走 Noto Serif SC 回退；英文装饰走 Cinzel Decorative
