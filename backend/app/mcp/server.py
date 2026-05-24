"""MCP Server — 将狼人杀后端暴露为 MCP Tools 供 LLM 调用"""

from __future__ import annotations

import json
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.game.engine import create_engine
from app.game.dealing import setup_game
from app.models.actions import Action, ActionType
from app.models.game import (
    GameState,
    GameStatus,
    Phase,
    Role,
    CreateGameRequest,
    CreateGameResponse,
    GameSummary,
    PlayerPublicInfo,
)
from app.services.game_registry import game_registry

mcp = FastMCP("werewolf", instructions="十人狼人杀 MVP — MCP Tools")


# ── MCP Tools ─────────────────────────────────────────────────


@mcp.tool()
async def create_game(player_name: str = "玩家", seed: int | None = None) -> str:
    """创建新对局并返回对局信息（game_id、玩家座位、角色）"""
    game_id = str(uuid.uuid4())
    player_token = str(uuid.uuid4())
    state, human_seat = game_registry.create(
        game_id,
        player_name=player_name,
        player_token=player_token,
        seed=seed,
    )
    human = state.get_player(human_seat)
    return json.dumps(
        {
            "game_id": game_id,
            "player_token": player_token,
            "human_seat": human_seat,
            "human_role": human.role.value if human.role else None,
            "ws_url": f"/ws/games/{game_id}?token={player_token}",
        },
        ensure_ascii=False,
    )


@mcp.tool()
async def get_game_summary(game_id: str) -> str:
    """获取对局摘要：阶段、存活玩家、公共日志"""
    state = game_registry.get(game_id)
    if state is None:
        return json.dumps({"error": "对局不存在"})
    summary = GameSummary(
        game_id=state.game_id,
        status=state.status.value,
        phase=state.phase.value,
        sub_phase=state.sub_phase.value if state.sub_phase else None,
        day_number=state.day_number,
        alive_count=len(state.alive_seats),
        players=[
            PlayerPublicInfo(
                seat=p.seat,
                name=p.name,
                is_alive=p.is_alive,
                is_human=p.is_human,
            )
            for p in state.players
        ],
        last_night_deaths=state.last_night_deaths,
        last_exiled_seat=state.last_exiled_seat,
    )
    return summary.model_dump_json()


@mcp.tool()
async def list_games() -> str:
    """列出所有活跃对局"""
    games = []
    from app.services.game_registry import game_registry

    for game_id in list(game_registry._games.keys()):
        state = game_registry.get(game_id)
        if state is None:
            continue
        games.append(
            {
                "game_id": game_id,
                "status": state.status.value,
                "phase": state.phase.value,
                "day": state.day_number,
                "alive": len(state.alive_seats),
            }
        )
    return json.dumps(games, ensure_ascii=False)


@mcp.tool()
async def get_player_view(game_id: str, seat: int) -> str:
    """获取指定玩家的合法视野"""
    from app.services.state_view import build_public_view

    state = game_registry.get(game_id)
    if state is None:
        return json.dumps({"error": "对局不存在"})
    view = build_public_view(state, seat)
    return json.dumps(view, ensure_ascii=False, default=str)


@mcp.tool()
async def submit_speech(game_id: str, seat: int, content: str, token: str = "") -> str:
    """提交玩家发言（仅人类玩家在自己回合可提交）"""
    state = game_registry.get(game_id)
    if state is None:
        return json.dumps({"error": "对局不存在"})

    if token and not game_registry.verify_token(game_id, token):
        return json.dumps({"error": "无效 token"})

    human_seat = game_registry.human_seat(game_id)
    if seat != human_seat:
        return json.dumps({"error": "只能提交自己的发言"})

    engine = create_engine(state)
    action = Action(
        action_type=ActionType.SPEECH,
        seat=seat,
        payload={"content": content},
    )
    result = engine.apply_action(action)
    return json.dumps(
        {"ok": result.ok, "message": result.message},
        ensure_ascii=False,
    )


@mcp.tool()
async def submit_vote(game_id: str, seat: int, target_seat: int, token: str = "") -> str:
    """提交放逐投票"""
    state = game_registry.get(game_id)
    if state is None:
        return json.dumps({"error": "对局不存在"})

    if token and not game_registry.verify_token(game_id, token):
        return json.dumps({"error": "无效 token"})

    human_seat = game_registry.human_seat(game_id)
    if seat != human_seat:
        return json.dumps({"error": "只能提交自己的投票"})

    engine = create_engine(state)
    action = Action(
        action_type=ActionType.VOTE,
        seat=seat,
        payload={"target_seat": target_seat},
    )
    result = engine.apply_action(action)
    return json.dumps({"ok": result.ok, "message": result.message}, ensure_ascii=False)


@mcp.tool()
async def get_public_log(game_id: str, limit: int = 30) -> str:
    """获取公共日志（发言、系统消息等）"""
    state = game_registry.get(game_id)
    if state is None:
        return json.dumps({"error": "对局不存在"})
    logs = [
        {"seat": e.seat, "type": e.type, "content": e.content, "turn": e.turn}
        for e in state.public_log[-limit:]
    ]
    return json.dumps(logs, ensure_ascii=False)


@mcp.tool()
async def health_check() -> str:
    """健康检查"""
    return json.dumps({"status": "ok"})


def run_stdio() -> None:
    """通过 stdio 运行 MCP Server（用于 Claude Desktop 等 Host）"""
    mcp.run(transport="stdio")


def run_sse(host: str = "0.0.0.0", port: int = 8001) -> None:
    """通过 SSE 运行 MCP Server"""
    mcp.run(transport="sse", host=host, port=port)