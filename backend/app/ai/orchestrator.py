"""AI 编排：有 LLM 时走 Pipeline，否则 Mock"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

from app.ai.belief import update_belief_from_public_log
from app.ai.memory import record_seer_check_truth, record_vote, record_wolf_nomination
from app.ai.private_channel import send_seer_result
from app.config import settings
from app.game.engine import ApplyResult, RuleEngine
from app.game.night_resolution import ensure_wolf_kill_target
from app.game.roles import find_role_seat
from app.game.simulator import pick_vote_target
from app.llm.client import LlmNotConfiguredError
from app.llm.pipeline import LlmPipeline, get_pipeline
from app.models.actions import Action, ActionType
from app.models.game import GameState, Player, Role, SubPhase
from app.services import auto_player

logger = logging.getLogger(__name__)

SendPrivateFn = Callable[[int, dict[str, Any]], Awaitable[None]] | None


def is_llm_enabled() -> bool:
    if not settings.has_llm_configured:
        return False
    from app.llm.health import llm_is_ready

    return llm_is_ready()


def _use_night_fast() -> bool:
    return settings.llm_night_fast_mode


def _use_vote_fast() -> bool:
    return settings.llm_vote_fast_mode


async def _night_action(
    pipe: LlmPipeline,
    engine: RuleEngine,
    seat: int,
    role: Role,
    schema: str,
) -> dict[str, Any]:
    if _use_night_fast():
        return await pipe.run_night_action_pipeline(
            engine.state, seat, role, schema, engine.rng
        )
    return await pipe.run_action_pipeline(engine.state, seat, role, schema, engine.rng)


async def _vote_action(
    pipe: LlmPipeline,
    engine: RuleEngine,
    seat: int,
    role: Role,
    schema: str,
) -> dict[str, Any]:
    if _use_vote_fast():
        return await pipe.run_vote_action_pipeline(
            engine.state, seat, role, schema, engine.rng
        )
    return await pipe.run_action_pipeline(engine.state, seat, role, schema, engine.rng)


def _alive_targets(state: GameState, seat: int) -> list[int]:
    return sorted(s for s in state.alive_seats if s != seat)


def _parse_target(data: dict[str, Any], state: GameState, seat: int, rng: random.Random) -> int | None:
    t = data.get("target_seat")
    if t is None:
        return None
    try:
        t = int(t)
    except (TypeError, ValueError):
        return rng.choice(_alive_targets(state, seat)) if _alive_targets(state, seat) else None
    if t in state.alive_seats:
        return t
    candidates = _alive_targets(state, seat)
    return rng.choice(candidates) if candidates else None


OnStreamDelta = Callable[[str], Awaitable[None]]


async def submit_speech(
    engine: RuleEngine,
    seat: int,
    pipeline: LlmPipeline | None = None,
    on_stream_delta: OnStreamDelta | None = None,
) -> None:
    state = engine.state
    player = state.get_player(seat)
    role = player.role or Role.VILLAGER

    if not is_llm_enabled():
        auto_player.auto_submit_speech(engine, seat)
        update_belief_from_public_log(state, seat)
        return

    pipe = pipeline or get_pipeline()
    try:
        if on_stream_delta is not None:
            content = await pipe.run_speech_pipeline_stream(
                state, seat, role, engine.rng, on_stream_delta
            )
        else:
            content = await pipe.run_speech_pipeline(state, seat, role, engine.rng)
    except (LlmNotConfiguredError, Exception) as exc:
        logger.warning("发言 LLM 失败 seat=%s: %s，降级 Mock", seat, exc)
        auto_player.auto_submit_speech(engine, seat)
    else:
        engine.apply_action(
            Action(action_type=ActionType.SPEECH, actor_seat=seat, content=content)
        )
    update_belief_from_public_log(state, seat)


async def submit_vote(
    engine: RuleEngine,
    seat: int,
    pipeline: LlmPipeline | None = None,
) -> None:
    state = engine.state
    player = state.get_player(seat)
    role = player.role or Role.VILLAGER

    target: int | None
    if not is_llm_enabled():
        target = pick_vote_target(state, seat, engine.rng)
    else:
        pipe = pipeline or get_pipeline()
        schema = (
            '{"action_type":"vote","target_seat":座位或null表示弃票,'
            '"extra":{}}'
        )
        try:
            data = await _vote_action(pipe, engine, seat, role, schema)
            if data.get("action_type") == "pass":
                target = None
            else:
                target = _parse_target(data, state, seat, engine.rng)
        except (LlmNotConfiguredError, Exception) as exc:
            logger.warning("投票 LLM 失败 seat=%s: %s", seat, exc)
            target = pick_vote_target(state, seat, engine.rng)

    engine.apply_action(
        Action(action_type=ActionType.VOTE, actor_seat=seat, target_seat=target)
    )
    record_vote(state, seat, target)


async def _plan_wolf_ai_turn(
    pipe: LlmPipeline,
    engine: RuleEngine,
    wolf: Player,
    candidates: list[int],
) -> tuple[int, int | None]:
    """单狼 LLM 规划（可并行），返回 (seat, target)。"""
    schema = '{"action_type":"wolf_nominate","target_seat":座位,"extra":{}}'
    try:
        data = await pipe.run_wolf_nominate_pipeline(
            engine.state, wolf.seat, schema, candidates, engine.rng
        )
        target = _parse_target(data, engine.state, wolf.seat, engine.rng) or (
            engine.rng.choice(candidates) if candidates else None
        )
        return wolf.seat, target
    except (LlmNotConfiguredError, Exception) as exc:
        logger.warning("狼刀 LLM 失败 seat=%s: %s", wolf.seat, exc)
        target = engine.rng.choice(candidates) if candidates else None
        return wolf.seat, target


async def _submit_wolf_nominations(
    engine: RuleEngine,
    human_seat: int,
    pipeline: LlmPipeline | None = None,
) -> None:
    state = engine.state
    wolf_seats = {w.seat for w in state.alive_wolves()}
    candidates = [s for s in sorted(state.alive_seats) if s not in wolf_seats]
    pipe = pipeline or get_pipeline()

    pending_wolves = [
        w
        for w in state.alive_wolves()
        if w.seat not in state.night_actions.wolf_nominations and not w.is_human
    ]

    if not pending_wolves:
        return

    if is_llm_enabled() and len(pending_wolves) > 1:
        plans = await asyncio.gather(
            *[_plan_wolf_ai_turn(pipe, engine, wolf, candidates) for wolf in pending_wolves]
        )
    else:
        plans = []
        for wolf in pending_wolves:
            if is_llm_enabled():
                plans.append(await _plan_wolf_ai_turn(pipe, engine, wolf, candidates))
            else:
                target = engine.rng.choice(candidates) if candidates else None
                plans.append((wolf.seat, target))

    for seat, target in plans:
        if target is None:
            continue
        engine.apply_action(
            Action(
                action_type=ActionType.WOLF_NOMINATE,
                actor_seat=seat,
                target_seat=target,
            )
        )
        record_wolf_nomination(state, seat, target)


async def _submit_seer(
    engine: RuleEngine,
    send_private: SendPrivateFn,
    pipeline: LlmPipeline | None = None,
) -> None:
    state = engine.state
    seer = find_role_seat(state, Role.SEER)
    if seer is None or seer not in state.alive_seats:
        return
    if state.night_actions.seer_check_target is not None:
        return
    player = state.get_player(seer)
    if player.is_human:
        return

    schema = '{"action_type":"seer_check","target_seat":座位,"extra":{}}'
    if is_llm_enabled():
        pipe = pipeline or get_pipeline()
        try:
            data = await _night_action(pipe, engine, seer, Role.SEER, schema)
            target = _parse_target(data, state, seer, engine.rng)
        except (LlmNotConfiguredError, Exception):
            target = engine.rng.choice(sorted(state.alive_seats))
    else:
        target = engine.rng.choice(sorted(state.alive_seats))

    if target is None:
        target = engine.rng.choice(sorted(state.alive_seats))

    engine.apply_action(
        Action(action_type=ActionType.SEER_CHECK, actor_seat=seer, target_seat=target)
    )

    check = state.seer_checks[-1] if state.seer_checks else None
    if check:
        record_seer_check_truth(state, seer, check.target_seat, check.is_wolf)
        await send_seer_result(state, seer, check.target_seat, check.is_wolf, send_private)


def _finish_witch_turn(engine: RuleEngine, witch: int, result: ApplyResult) -> None:
    """女巫每夜仅一次决策：成功则结束；失败则本 tick 内降级为跳过，不再二次 LLM。"""
    if result.ok:
        return
    logger.info(
        "witch action rejected seat=%s msg=%s, applying pass",
        witch,
        result.message,
    )
    engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=witch))


async def _submit_witch(engine: RuleEngine, pipeline: LlmPipeline | None = None) -> None:
    state = engine.state
    witch = find_role_seat(state, Role.WITCH)
    if witch is None or witch not in state.alive_seats:
        return
    if state.night_actions.witch_done:
        return
    if state.get_player(witch).is_human:
        return

    ensure_wolf_kill_target(state, engine.rng)

    if is_llm_enabled():
        pipe = pipeline or get_pipeline()
        schema = (
            '{"action_type":"witch_heal|witch_poison|pass",'
            '"target_seat":座位或null,"extra":{"use_heal":bool}}'
        )
        try:
            data = await _night_action(pipe, engine, witch, Role.WITCH, schema)
            at = data.get("action_type", "pass")
            target = _parse_target(data, state, witch, engine.rng)
            if at == "witch_heal" and target and state.witch_state.heal_available:
                result = engine.apply_action(
                    Action(action_type=ActionType.WITCH_HEAL, actor_seat=witch, target_seat=target)
                )
                _finish_witch_turn(engine, witch, result)
                return
            if at == "witch_poison" and target and state.witch_state.poison_available:
                result = engine.apply_action(
                    Action(
                        action_type=ActionType.WITCH_POISON,
                        actor_seat=witch,
                        target_seat=target,
                    )
                )
                _finish_witch_turn(engine, witch, result)
                return
        except (LlmNotConfiguredError, Exception) as exc:
            logger.warning("女巫 LLM 失败 seat=%s: %s", witch, exc)

    engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=witch))


async def _submit_guard(engine: RuleEngine, pipeline: LlmPipeline | None = None) -> None:
    state = engine.state
    guard = find_role_seat(state, Role.GUARD)
    if guard is None or guard not in state.alive_seats:
        return
    if state.night_actions.guard_done:
        return
    if state.get_player(guard).is_human:
        return

    candidates = [s for s in state.alive_seats if s != state.guard_last_target]
    target: int | None = None

    if is_llm_enabled() and candidates:
        pipe = pipeline or get_pipeline()
        schema = '{"action_type":"guard_protect","target_seat":座位,"extra":{}}'
        try:
            data = await _night_action(pipe, engine, guard, Role.GUARD, schema)
            target = _parse_target(data, state, guard, engine.rng)
        except (LlmNotConfiguredError, Exception):
            target = None

    if target is None and candidates:
        target = engine.rng.choice(list(candidates))
    if target:
        engine.apply_action(
            Action(action_type=ActionType.GUARD_PROTECT, actor_seat=guard, target_seat=target)
        )
    else:
        engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=guard))


async def submit_night_for_ai(
    engine: RuleEngine,
    human_seat: int,
    send_private: SendPrivateFn = None,
    pipeline: LlmPipeline | None = None,
) -> bool:
    if not is_llm_enabled():
        return auto_player.auto_submit_night_for_ai(engine, human_seat)

    state = engine.state
    sub = state.sub_phase

    if sub == SubPhase.NIGHT_WOLF:
        await _submit_wolf_nominations(engine, human_seat, pipeline)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.NIGHT_SEER:
        seer = find_role_seat(state, Role.SEER)
        if seer == human_seat and seer in state.alive_seats:
            return state.night_actions.seer_check_target is not None
        await _submit_seer(engine, send_private, pipeline)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.NIGHT_WITCH:
        witch = find_role_seat(state, Role.WITCH)
        if witch == human_seat and witch in state.alive_seats:
            return state.night_actions.witch_done
        await _submit_witch(engine, pipeline)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.NIGHT_GUARD:
        guard = find_role_seat(state, Role.GUARD)
        if guard == human_seat and guard in state.alive_seats:
            return state.night_actions.guard_done
        await _submit_guard(engine, pipeline)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.HUNTER_SHOOT:
        hunter = state.pending_hunter_seat
        if hunter == human_seat:
            return False
        auto_player._submit_hunter_pass(engine)
        return engine.is_sub_phase_complete()

    return True
