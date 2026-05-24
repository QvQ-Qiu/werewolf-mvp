"""夜晚结算辅助：狼刀预估、结构化日志、死因文案"""

from __future__ import annotations

import logging
import random

from app.game.voting import resolve_wolf_kill
from app.models.game import GameState, SubPhase

logger = logging.getLogger(__name__)


def ensure_wolf_kill_target(state: GameState, rng: random.Random) -> int | None:
    """
    在女巫/守卫阶段前，根据狼刀提名推算当夜刀口（与终局结算一致）。
    若提名未齐或尚无狼人，返回 None。
    """
    if state.wolf_kill_target is not None:
        return state.wolf_kill_target
    wolves = state.alive_wolves()
    if not wolves:
        return None
    noms = state.night_actions.wolf_nominations
    if not all(w.seat in noms for w in wolves):
        return None
    target = resolve_wolf_kill(state, rng)
    state.wolf_kill_target = target
    logger.info(
        "night wolf_kill_target resolved day=%s target=%s nominations=%s",
        state.day_number,
        target,
        dict(noms),
    )
    return target


def build_night_death_reasons(state: GameState, deaths: list[int]) -> dict[int, str]:
    """根据结算真相生成公屏死因（狼刀 / 毒杀 / 同守同救）。"""
    reasons: dict[int, str] = {}
    wolf_target = state.wolf_kill_target
    guard_target = state.night_actions.guard_protect_target
    heal_target = state.night_actions.witch_heal_target
    poison_target = state.night_actions.witch_poison_target

    for seat in deaths:
        if poison_target == seat:
            reasons[seat] = "毒杀"
        elif seat == wolf_target:
            if (
                guard_target == wolf_target
                and heal_target == wolf_target
                and guard_target is not None
            ):
                reasons[seat] = "狼刀（同守同救）"
            else:
                reasons[seat] = "狼刀"
        else:
            reasons[seat] = "夜间"
    return reasons


def log_sub_phase_enter(state: GameState, sub: SubPhase) -> None:
    logger.info(
        "night sub_phase enter day=%s sub=%s",
        state.day_number,
        sub.value,
    )


def log_sub_phase_complete(state: GameState, sub: SubPhase, msg: str) -> None:
    logger.info(
        "night sub_phase complete day=%s sub=%s msg=%s",
        state.day_number,
        sub.value,
        msg,
    )


def log_night_actions_snapshot(state: GameState) -> None:
    na = state.night_actions
    logger.info(
        "night actions snapshot day=%s wolf_nominations=%s seer=%s "
        "witch_heal=%s witch_poison=%s guard=%s wolf_kill_target=%s",
        state.day_number,
        dict(na.wolf_nominations),
        na.seer_check_target,
        na.witch_heal_target,
        na.witch_poison_target,
        na.guard_protect_target,
        state.wolf_kill_target,
    )


def log_resolve_night_deaths(
    state: GameState,
    deaths: list[int],
    reasons: dict[int, str],
) -> None:
    logger.info(
        "night resolve_deaths day=%s wolf_kill=%s guard=%s heal=%s poison=%s "
        "deaths=%s reasons=%s",
        state.day_number,
        state.wolf_kill_target,
        state.night_actions.guard_protect_target,
        state.night_actions.witch_heal_target,
        state.night_actions.witch_poison_target,
        deaths,
        reasons,
    )
