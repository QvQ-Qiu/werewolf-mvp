"""Mock AI 自动行动（无 QWEN_API_KEY 时由 orchestrator 降级调用）"""

from __future__ import annotations

import random

from app.game.engine import RuleEngine
from app.game.roles import find_role_seat
from app.game.simulator import pick_vote_target
from app.models.actions import Action, ActionType
from app.models.game import GameState, Role, SubPhase


def mock_speech_content(seat: int, state: GameState | None = None) -> str:
    """固定发言模板；若提供 state 则引用已过麦座位，避免期待其再发言。"""
    if state is not None and state.speech_order and state.current_speaker_index > 0:
        done = state.speech_order[: state.current_speaker_index]
        if done:
            refs = "、".join(f"{s}号" for s in done[-2:])
            return f"{seat}号：听了{refs}的发言，我先记录一下，再听后面几位。"
    return f"{seat}号：我觉得场上信息还不够，先听大家发言。"


def _submit_wolf_nominations(engine: RuleEngine) -> None:
    state = engine.state
    rng = engine.rng
    wolf_seats = {w.seat for w in state.alive_wolves()}
    candidates = [s for s in sorted(state.alive_seats) if s not in wolf_seats]
    if not candidates:
        return
    for wolf in state.alive_wolves():
        if wolf.seat not in state.night_actions.wolf_nominations:
            target = rng.choice(candidates)
            engine.apply_action(
                Action(
                    action_type=ActionType.WOLF_NOMINATE,
                    actor_seat=wolf.seat,
                    target_seat=target,
                )
            )


def _submit_seer_check(engine: RuleEngine) -> None:
    state = engine.state
    seer = find_role_seat(state, Role.SEER)
    if seer is None or seer not in state.alive_seats:
        return
    if state.night_actions.seer_check_target is not None:
        return
    target = engine.rng.choice(sorted(state.alive_seats))
    engine.apply_action(
        Action(action_type=ActionType.SEER_CHECK, actor_seat=seer, target_seat=target)
    )


def _submit_witch_pass(engine: RuleEngine) -> None:
    state = engine.state
    witch = find_role_seat(state, Role.WITCH)
    if witch is None or witch not in state.alive_seats:
        return
    if state.night_actions.witch_done:
        return
    engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=witch))


def _submit_guard(engine: RuleEngine) -> None:
    state = engine.state
    guard = find_role_seat(state, Role.GUARD)
    if guard is None or guard not in state.alive_seats:
        return
    if state.night_actions.guard_done:
        return
    candidates = [s for s in state.alive_seats if s != state.guard_last_target]
    if candidates:
        target = engine.rng.choice(candidates)
        engine.apply_action(
            Action(action_type=ActionType.GUARD_PROTECT, actor_seat=guard, target_seat=target)
        )
    else:
        engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=guard))


def _submit_hunter_pass(engine: RuleEngine) -> None:
    state = engine.state
    hunter = state.pending_hunter_seat
    if hunter is None:
        return
    engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=hunter))


def auto_submit_night_for_ai(engine: RuleEngine, human_seat: int) -> bool:
    """
    为当前夜晚子阶段提交所有 AI 行动（不推进阶段）。
    若子阶段需要人类输入则返回 False。
    """
    state = engine.state
    sub = state.sub_phase

    if sub == SubPhase.NIGHT_WOLF:
        _submit_wolf_nominations(engine)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.NIGHT_SEER:
        seer = find_role_seat(state, Role.SEER)
        if seer is None or seer not in state.alive_seats:
            return True
        if seer == human_seat:
            return state.night_actions.seer_check_target is not None
        _submit_seer_check(engine)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.NIGHT_WITCH:
        witch = find_role_seat(state, Role.WITCH)
        if witch is None or witch not in state.alive_seats:
            return True
        if witch == human_seat:
            return state.night_actions.witch_done
        _submit_witch_pass(engine)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.NIGHT_GUARD:
        guard = find_role_seat(state, Role.GUARD)
        if guard is None or guard not in state.alive_seats:
            return True
        if guard == human_seat:
            return state.night_actions.guard_done
        _submit_guard(engine)
        return engine.is_sub_phase_complete()

    if sub == SubPhase.HUNTER_SHOOT:
        hunter = state.pending_hunter_seat
        if hunter is None:
            return True
        if hunter == human_seat:
            return False
        _submit_hunter_pass(engine)
        return engine.is_sub_phase_complete()

    return True


def auto_submit_human_night(engine: RuleEngine, human_seat: int) -> None:
    """人类超时未操作时自动提交默认夜晚行动"""
    state = engine.state
    sub = state.sub_phase
    rng = engine.rng

    if sub == SubPhase.NIGHT_WOLF:
        wolf_seats = {w.seat for w in state.alive_wolves()}
        candidates = [s for s in sorted(state.alive_seats) if s not in wolf_seats]
        if candidates:
            engine.apply_action(
                Action(
                    action_type=ActionType.WOLF_NOMINATE,
                    actor_seat=human_seat,
                    target_seat=rng.choice(candidates),
                )
            )
        else:
            engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=human_seat))
    elif sub == SubPhase.NIGHT_SEER:
        engine.apply_action(
            Action(
                action_type=ActionType.SEER_CHECK,
                actor_seat=human_seat,
                target_seat=rng.choice(sorted(state.alive_seats)),
            )
        )
    elif sub == SubPhase.NIGHT_WITCH:
        if state.wolf_kill_target and state.witch_state.heal_available:
            engine.apply_action(
                Action(
                    action_type=ActionType.WITCH_HEAL,
                    actor_seat=human_seat,
                    target_seat=state.wolf_kill_target,
                )
            )
        else:
            engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=human_seat))
    elif sub == SubPhase.NIGHT_GUARD:
        candidates = [s for s in state.alive_seats if s != state.guard_last_target]
        if candidates:
            engine.apply_action(
                Action(
                    action_type=ActionType.GUARD_PROTECT,
                    actor_seat=human_seat,
                    target_seat=rng.choice(candidates),
                )
            )
        else:
            engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=human_seat))
    elif sub == SubPhase.HUNTER_SHOOT:
        engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=human_seat))


def auto_submit_speech(engine: RuleEngine, seat: int) -> None:
    engine.apply_action(
        Action(
            action_type=ActionType.SPEECH,
            actor_seat=seat,
            content=mock_speech_content(seat, engine.state),
        )
    )


def auto_submit_vote(engine: RuleEngine, seat: int, rng: random.Random) -> None:
    target = pick_vote_target(engine.state, seat, rng)
    engine.apply_action(
        Action(action_type=ActionType.VOTE, actor_seat=seat, target_seat=target)
    )


def needs_human_night_action(state: GameState, human_seat: int) -> tuple[str, int] | None:
    """若当前夜晚子阶段等待人类行动，返回 (action_type, actor_seat)"""
    sub = state.sub_phase
    if sub == SubPhase.NIGHT_WOLF:
        player = state.get_player(human_seat)
        if player.is_alive and player.role == Role.WOLF:
            if human_seat not in state.night_actions.wolf_nominations:
                return ("wolf_nominate", human_seat)
    if sub == SubPhase.NIGHT_SEER:
        seer = find_role_seat(state, Role.SEER)
        if seer == human_seat and seer in state.alive_seats:
            if state.night_actions.seer_check_target is None:
                return ("seer_check", human_seat)
    if sub == SubPhase.NIGHT_WITCH:
        witch = find_role_seat(state, Role.WITCH)
        if witch == human_seat and witch in state.alive_seats:
            if not state.night_actions.witch_done:
                return ("witch_action", human_seat)
    if sub == SubPhase.NIGHT_GUARD:
        guard = find_role_seat(state, Role.GUARD)
        if guard == human_seat and guard in state.alive_seats:
            if not state.night_actions.guard_done:
                return ("guard_protect", human_seat)
    if sub == SubPhase.HUNTER_SHOOT and state.pending_hunter_seat == human_seat:
        return ("hunter_shoot", human_seat)
    return None
