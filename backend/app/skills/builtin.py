"""内置 Skill — OpenClaw 集成 Skill"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class CreateGameSkill(BaseSkill):
    """创建狼人杀对局"""

    name = "create_game"
    description = "创建新的十人狼人杀对局，返回对局 ID 和玩家信息"
    category = "game"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        from app.services.game_registry import game_registry

        import uuid

        player_name = ctx.params.get("player_name", "玩家")
        seed = ctx.params.get("seed")
        game_id = str(uuid.uuid4())
        player_token = str(uuid.uuid4())
        state, human_seat = game_registry.create(
            game_id, player_name=player_name, player_token=player_token, seed=seed
        )
        human = state.get_player(human_seat)
        return SkillResult(
            success=True,
            data={
                "game_id": game_id,
                "player_token": player_token,
                "human_seat": human_seat,
                "human_role": human.role.value if human.role else None,
                "ws_url": f"/ws/games/{game_id}?token={player_token}",
            },
        )


class GetGameStateSkill(BaseSkill):
    """获取对局状态快照"""

    name = "get_game_state"
    description = "获取指定对局的当前状态：阶段、存活玩家、公共日志等"
    category = "game"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        from app.services.game_registry import game_registry

        game_id = ctx.params.get("game_id")
        if not game_id:
            return SkillResult(success=False, message="缺少 game_id")
        state = game_registry.get(game_id)
        if state is None:
            return SkillResult(success=False, message=f"对局 {game_id} 不存在")
        return SkillResult(
            success=True,
            data={
                "game_id": state.game_id,
                "status": state.status.value,
                "phase": state.phase.value,
                "sub_phase": state.sub_phase.value if state.sub_phase else None,
                "day_number": state.day_number,
                "alive_seats": sorted(state.alive_seats),
                "alive_count": len(state.alive_seats),
                "total_players": len(state.players),
                "last_night_deaths": state.last_night_deaths,
                "last_exiled_seat": state.last_exiled_seat,
            },
        )


class ListGamesSkill(BaseSkill):
    """列出所有活跃对局"""

    name = "list_games"
    description = "列出当前所有活跃的狼人杀对局"
    category = "game"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        from app.services.game_registry import game_registry

        games = []
        for gid in list(game_registry._games.keys()):
            state = game_registry.get(gid)
            if state is None:
                continue
            games.append(
                {
                    "game_id": gid,
                    "status": state.status.value,
                    "phase": state.phase.value,
                    "day": state.day_number,
                    "alive": len(state.alive_seats),
                }
            )
        return SkillResult(success=True, data={"games": games, "count": len(games)})


class SubmitVoteSkill(BaseSkill):
    """提交放逐投票"""

    name = "submit_vote"
    description = "提交放逐投票：指定对局、玩家座位、投票目标"
    category = "game"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        from app.game.engine import create_engine
        from app.models.actions import Action, ActionType

        game_id = ctx.params.get("game_id")
        seat = ctx.params.get("seat")
        target_seat = ctx.params.get("target_seat")
        if not all([game_id, seat, target_seat]):
            return SkillResult(success=False, message="缺少参数: game_id, seat, target_seat")
        from app.services.game_registry import game_registry

        state = game_registry.get(game_id)
        if state is None:
            return SkillResult(success=False, message=f"对局 {game_id} 不存在")
        engine = create_engine(state)
        action = Action(
            action_type=ActionType.VOTE,
            seat=seat,
            payload={"target_seat": target_seat},
        )
        result = engine.apply_action(action)
        return SkillResult(success=result.ok, message=result.message)


class GetPublicLogSkill(BaseSkill):
    """获取公共日志"""

    name = "get_public_log"
    description = "获取指定对局的公共日志（发言、系统消息、投票等）"
    category = "game"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        from app.services.game_registry import game_registry

        game_id = ctx.params.get("game_id")
        limit = ctx.params.get("limit", 30)
        if not game_id:
            return SkillResult(success=False, message="缺少 game_id")
        state = game_registry.get(game_id)
        if state is None:
            return SkillResult(success=False, message=f"对局 {game_id} 不存在")
        logs = [
            {"seat": e.seat, "type": e.type, "content": e.content, "turn": e.turn}
            for e in state.public_log[-limit:]
        ]
        return SkillResult(success=True, data={"logs": logs, "count": len(logs)})


class HealthCheckSkill(BaseSkill):
    """健康检查"""

    name = "health_check"
    description = "检查后端服务是否健康运行"
    category = "system"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        return SkillResult(success=True, data={"status": "ok"})