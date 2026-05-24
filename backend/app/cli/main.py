"""Native CLI — 狼人杀后端命令行工具"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import click

from app.game.engine import create_engine
from app.models.actions import Action, ActionType
from app.models.game import (
    GameState,
    GameStatus,
    Phase,
    Role,
)
from app.services.game_registry import game_registry


# ── 辅助函数 ───────────────────────────────────────────────


def _get_state(game_id: str) -> GameState:
    state = game_registry.get(game_id)
    if state is None:
        raise click.ClickException(f"对局 {game_id} 不存在")
    return state


def _print_state(state: GameState) -> None:
    click.echo("=" * 50)
    click.echo(f"对局: {state.game_id}")
    click.echo(f"状态: {state.status.value} | 阶段: {state.phase.value}")
    click.echo(f"子阶段: {state.sub_phase.value if state.sub_phase else '-'}")
    click.echo(f"天数: {state.day_number}")
    click.echo(f"存活: {len(state.alive_seats)}/{len(state.players)}")
    click.echo(f"昨夜死亡: {state.last_night_deaths or '-'}")
    click.echo(f"昨放逐: {state.last_exiled_seat or '-'}")
    click.echo("-" * 50)
    for p in state.players:
        role_str = p.role.value if p.role else "?"
        alive_str = "●" if p.is_alive else "○"
        human_str = " [人]" if p.is_human else ""
        click.echo(f"  {alive_str} 座{p.seat} {p.name:8s} | {role_str}{human_str}")
    click.echo("=" * 50)


# ── CLI 命令 ───────────────────────────────────────────────


@click.group()
def cli() -> None:
    """狼人杀后端 CLI — 管理对局、查看状态、模拟运行"""


@cli.command()
@click.option("--name", default="玩家", help="玩家名称")
@click.option("--seed", default=None, type=int, help="随机种子（用于复现）")
def create(name: str, seed: int | None) -> None:
    """创建新对局"""
    game_id = str(uuid.uuid4())
    player_token = str(uuid.uuid4())
    state, human_seat = game_registry.create(
        game_id,
        player_name=name,
        player_token=player_token,
        seed=seed,
    )
    human = state.get_player(human_seat)
    click.echo(f"✅ 对局已创建: {game_id}")
    click.echo(f"   玩家座位: {human_seat}")
    click.echo(f"   玩家角色: {human.role.value if human.role else '?'}")
    click.echo(f"   Token: {player_token}")
    click.echo(f"   WS: /ws/games/{game_id}?token={player_token}")
    _print_state(state)


@cli.command()
@click.argument("game_id")
def status(game_id: str) -> None:
    """查看对局状态"""
    state = _get_state(game_id)
    _print_state(state)


@cli.command(name="list")
def list_games() -> None:
    """列出所有活跃对局"""
    games = []
    for gid in list(game_registry._games.keys()):
        state = game_registry.get(gid)
        if state is None:
            continue
        games.append(
            {
                "id": gid[:8] + "...",
                "status": state.status.value,
                "phase": state.phase.value,
                "day": state.day_number,
                "alive": f"{len(state.alive_seats)}/{len(state.players)}",
            }
        )
    if not games:
        click.echo("暂无活跃对局")
        return
    for g in games:
        click.echo(f"  {g['id']:12s} {g['status']:10s} {g['phase']:10s}  Day {g['day']}  {g['alive']}")


@cli.command()
@click.argument("game_id")
@click.argument("seat", type=int)
@click.argument("content")
def speech(game_id: str, seat: int, content: str) -> None:
    """提交发言"""
    state = _get_state(game_id)
    engine = create_engine(state)
    action = Action(
        action_type=ActionType.SPEECH,
        seat=seat,
        payload={"content": content},
    )
    result = engine.apply_action(action)
    if result.ok:
        click.echo("✅ 发言已提交")
    else:
        click.echo(f"❌ {result.message}")


@cli.command()
@click.argument("game_id")
@click.argument("seat", type=int)
@click.argument("target", type=int)
def vote(game_id: str, seat: int, target: int) -> None:
    """提交放逐投票"""
    state = _get_state(game_id)
    engine = create_engine(state)
    action = Action(
        action_type=ActionType.VOTE,
        seat=seat,
        payload={"target_seat": target},
    )
    result = engine.apply_action(action)
    if result.ok:
        click.echo(f"✅ 投票已提交: {seat} → {target}")
    else:
        click.echo(f"❌ {result.message}")


@cli.command()
@click.argument("game_id")
def log(game_id: str) -> None:
    """查看公共日志"""
    state = _get_state(game_id)
    for entry in state.public_log[-50:]:
        ts = entry.turn or ""
        seat = f"[座{entry.seat}]" if entry.seat else ""
        click.echo(f"  {ts:4s} {seat:6s} {entry.type:12s} {entry.content}")


@cli.command()
@click.option("--rounds", default=3, help="模拟轮数")
@click.option("--seed", default=42, type=int, help="随机种子")
def simulate(rounds: int, seed: int) -> None:
    """模拟完整对局"""
    from app.game.simulator import simulate_full_game

    click.echo(f"🎲 模拟对局 (seed={seed}, max_rounds={rounds})...")
    state = simulate_full_game(seed=seed, max_rounds=rounds)

    click.echo(f"\n✅ 对局结束")
    click.echo(f"  总轮数: {state.day_number}")
    click.echo(f"  胜方: {state.winner or '未知'}")
    click.echo(f"  日志条数: {len(state.public_log)}")
    _print_state(state)


@cli.command()
@click.option("--host", default="0.0.0.0", help="监听地址")
@click.option("--port", default=8000, type=int, help="监听端口")
@click.option("--reload", is_flag=True, help="热重载")
def serve(host: str, port: int, reload: bool) -> None:
    """启动 FastAPI 服务"""
    import uvicorn

    click.echo(f"🚀 启动服务 {host}:{port} (reload={reload})")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
def mcp() -> None:
    """启动 MCP Server (stdio 模式)"""
    from app.mcp.server import run_stdio

    click.echo("🧩 启动 MCP Server (stdio)...")
    run_stdio()


@cli.command()
@click.argument("game_id")
@click.argument("seat", type=int)
def view(game_id: str, seat: int) -> None:
    """查看玩家视野"""
    from app.services.state_view import build_public_view

    state = _get_state(game_id)
    view = build_public_view(state, seat)
    click.echo(json.dumps(view, ensure_ascii=False, indent=2, default=str))


# ── Coze CLI 子命令 ─────────────────────────────────────


@cli.group()
def coze() -> None:
    """Coze CLI 封装 — 登录、配置、生成、项目、文件"""


@coze.command()
def check() -> None:
    """检查 coze CLI 是否已安装"""
    from app.skills.coze.adapter import check_coze_installed, get_coze_version

    installed = check_coze_installed()
    if installed:
        click.echo(f"coze CLI 已安装 (版本: {get_coze_version()})")
    else:
        click.echo("coze CLI 未安装")
        click.echo("   请执行: npm install -g @coze/cli")


@coze.command(name="auth-status")
def coze_auth_status() -> None:
    """检查 Coze 登录状态"""
    from app.skills.coze.adapter import check_auth_status

    status = check_auth_status()
    click.echo(json.dumps(status, ensure_ascii=False, indent=2))


@coze.command()
@click.option("--org-id", default=None, help="组织 ID")
@click.option("--space-id", default=None, help="空间 ID")
def config(org_id: str | None, space_id: str | None) -> None:
    """查看 Coze 配置"""
    from app.skills.coze.adapter import get_config

    cfg = get_config()
    click.echo(json.dumps(cfg, ensure_ascii=False, indent=2))


@coze.command(name="org-list")
def coze_org_list() -> None:
    """列出可用组织"""
    from app.skills.coze.adapter import list_organizations

    orgs = list_organizations()
    if not orgs:
        click.echo("暂无可用组织")
        return
    for org in orgs:
        click.echo(f"  {org.get('id', '?'):20s} {org.get('name', '?')}")


@coze.command(name="space-list")
def coze_space_list() -> None:
    """列出可用空间"""
    from app.skills.coze.adapter import list_spaces

    spaces = list_spaces()
    if not spaces:
        click.echo("暂无可用空间")
        return
    for sp in spaces:
        click.echo(f"  {sp.get('id', '?'):20s} {sp.get('name', '?')}")


@coze.command()
@click.argument("args", nargs=-1, required=True)
def raw(args: tuple[str, ...]) -> None:
    """执行原始 coze 命令"""
    from app.skills.coze.adapter import run_coze_json, CozeCLIError

    try:
        result = run_coze_json(list(args))
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    except CozeCLIError as e:
        click.echo(f"错误 (exit={e.exit_code}): {e}", err=True)


# ── LLM 子命令 ───────────────────────────────────────


@cli.group()
def llm() -> None:
    """LLM 对话 — 调用豆包/OpenAI 兼容大模型"""


@llm.command()
@click.option("--api-key", envvar="ARK_API_KEY", required=True, help="API Key")
@click.option("--model", default="doubao-seed-2-0-mini-260215", help="模型名称")
@click.option("--base-url", default="https://ark.cn-beijing.volces.com/api/v3", help="API 地址")
@click.option("--system", "system_prompt", default="", help="系统提示词")
@click.argument("prompt")
def chat(
    api_key: str,
    model: str,
    base_url: str,
    system_prompt: str,
    prompt: str,
) -> None:
    """LLM 对话 — 发送 prompt 并打印回复"""
    from app.llm.client import LLMConfig, LLMClient, ChatMessage

    config = LLMConfig(api_key=api_key, base_url=base_url, model=model)
    client = LLMClient(config)
    try:
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        with click.progressbar(length=1, label="等待回复") as bar:
            result = client.chat(messages)
            bar.update(1)

        click.echo(f"\n[{result.model}]")
        click.echo(result.content)

        if result.usage:
            usage = result.usage
            click.echo(
                f"\n[Tokens: ↑{usage.get('prompt_tokens',0)} / ↓{usage.get('completion_tokens',0)}"
                f" / 共{usage.get('total_tokens',0)}]"
            )
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
    finally:
        client.close()


@llm.command(name="list-models")
@click.option("--api-key", envvar="ARK_API_KEY", required=True, help="API Key")
@click.option("--base-url", default="https://ark.cn-beijing.volces.com/api/v3", help="API 地址")
def list_models(api_key: str, base_url: str) -> None:
    """列出可用模型"""
    from app.llm.client import LLMConfig, LLMClient

    config = LLMConfig(api_key=api_key, base_url=base_url)
    client = LLMClient(config)
    try:
        models = client.list_models()
        if not models:
            click.echo("未获取到模型列表")
            return
        for m in models:
            click.echo(f"  {m.get('id', '?'):40s} {m.get('owned_by', '')}")
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
    finally:
        client.close()


if __name__ == "__main__":
    cli()