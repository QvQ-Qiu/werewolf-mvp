"""阶段转换状态机"""

from app.models.game import GameState, Phase, SubPhase
from app.game.night_resolution import (
    build_night_death_reasons,
    ensure_wolf_kill_target,
    log_night_actions_snapshot,
    log_resolve_night_deaths,
    log_sub_phase_complete,
    log_sub_phase_enter,
)
from app.game.roles import (
    announce_night_deaths,
    apply_night_deaths,
    build_speech_order,
    reset_day_actions,
    reset_night_actions,
    resolve_night_deaths,
    resolve_seer_check,
    should_hunter_shoot_exile,
    should_hunter_shoot_night,
)
from app.game.voting import resolve_wolf_kill
from app.game.win_condition import check_winner
import random


# 夜晚行动子阶段：狼人 → 预言家 → 女巫 → 守卫 → 结算（见 roles.resolve_night_deaths）
NIGHT_FLOW = [
    SubPhase.NIGHT_WOLF,
    SubPhase.NIGHT_SEER,
    SubPhase.NIGHT_WITCH,
    SubPhase.NIGHT_GUARD,
    SubPhase.NIGHT_RESOLVE,
]

DAY_FLOW = [
    SubPhase.DAY_ANNOUNCE,
    SubPhase.DAY_SPEECH,
    SubPhase.DAY_VOTE,
    SubPhase.DAY_RESOLVE,
]


def _next_in_flow(current: SubPhase, flow: list[SubPhase]) -> SubPhase | None:
    try:
        idx = flow.index(current)
    except ValueError:
        return None
    if idx + 1 < len(flow):
        return flow[idx + 1]
    return None


def _set_winner(state: GameState, winner) -> None:
    state.winner = winner
    state.phase = Phase.GAME_OVER
    state.sub_phase = None
    from app.models.game import GameStatus

    state.status = GameStatus.FINISHED


def advance_sub_phase(state: GameState, rng: random.Random) -> str:
    """
    推进到下一子阶段，必要时触发结算。
    返回操作说明消息。
    """
    if state.phase == Phase.GAME_OVER:
        return "对局已结束"

    sub = state.sub_phase
    if sub is None:
        return "无当前子阶段"

    # 夜晚流转
    if sub in NIGHT_FLOW:
        if sub == SubPhase.NIGHT_RESOLVE:
            return _resolve_night(state, rng)

        nxt = _next_in_flow(sub, NIGHT_FLOW)
        if nxt == SubPhase.NIGHT_SEER:
            ensure_wolf_kill_target(state, rng)
        if nxt == SubPhase.NIGHT_RESOLVE:
            if state.wolf_kill_target is None:
                state.wolf_kill_target = resolve_wolf_kill(state, rng)
            resolve_seer_check(state)
        if nxt:
            log_sub_phase_complete(state, sub, f"-> {nxt.value}")
            state.sub_phase = nxt
            log_sub_phase_enter(state, nxt)
            if nxt == SubPhase.NIGHT_RESOLVE:
                return _resolve_night(state, rng)
            return f"进入 {nxt.value}"
        return "夜晚流转结束"

    # 白天流转
    if sub in DAY_FLOW:
        if sub == SubPhase.DAY_ANNOUNCE:
            state.speech_order = build_speech_order(state)
            state.current_speaker_index = 0
            state.sub_phase = SubPhase.DAY_SPEECH
            return "死讯公布完成，进入发言"

        if sub == SubPhase.DAY_SPEECH:
            state.sub_phase = SubPhase.DAY_VOTE
            return "发言结束，进入投票"

        if sub == SubPhase.DAY_VOTE:
            state.sub_phase = SubPhase.DAY_RESOLVE
            return "投票收集完成，进入计票"

        if sub == SubPhase.DAY_RESOLVE:
            return _resolve_day(state, rng)

    if sub == SubPhase.HUNTER_SHOOT:
        return _after_hunter_shoot(state, rng)

    return f"未知子阶段 {sub}"


def _resolve_night(state: GameState, rng: random.Random) -> str:
    """夜结算"""
    log_night_actions_snapshot(state)
    deaths = resolve_night_deaths(state)
    reasons = build_night_death_reasons(state, deaths)
    log_resolve_night_deaths(state, deaths, reasons)
    apply_night_deaths(state, deaths, reasons)
    announce_night_deaths(state, deaths)

    # 检查猎人夜杀开枪
    for seat in deaths:
        if should_hunter_shoot_night(state, seat):
            state.pending_hunter_seat = seat
            state.sub_phase = SubPhase.HUNTER_SHOOT
            return f"{seat}号猎人可开枪"

    winner = check_winner(state)
    if winner:
        _set_winner(state, winner)
        return f"对局结束，{winner.value} 胜"

    # 进入白天
    state.phase = Phase.DAY
    state.day_number += 1
    reset_day_actions(state)
    state.sub_phase = SubPhase.DAY_ANNOUNCE
    return f"第 {state.day_number} 天开始"


def _resolve_day(state: GameState, rng: random.Random) -> str:
    """日结算：计票放逐"""
    from app.game.voting import format_vote_summary, tally_day_votes
    from app.game.roles import exile_player

    exiled, vote_counts, is_tie = tally_day_votes(state)
    _log_votes(state, vote_counts)

    if is_tie:
        _announce_tie(state)
        return _go_to_next_night(state, rng)

    if exiled is not None:
        exile_player(state, exiled)
        if should_hunter_shoot_exile(state, exiled):
            state.pending_hunter_seat = exiled
            state.sub_phase = SubPhase.HUNTER_SHOOT
            return f"{exiled}号猎人被放逐，可开枪"

    winner = check_winner(state)
    if winner:
        _set_winner(state, winner)
        return f"对局结束，{winner.value} 胜"

    return _go_to_next_night(state, rng)


def _log_votes(state: GameState, vote_counts: dict[int, int]) -> None:
    from app.game.voting import format_vote_summary

    content = format_vote_summary(vote_counts, state.day_votes)
    from app.game.roles import _log

    _log(state, content, "vote")


def _announce_tie(state: GameState) -> None:
    from app.game.roles import _log

    _log(state, "投票平票，本日无人出局")


def _go_to_next_night(state: GameState, rng: random.Random) -> str:
    state.phase = Phase.NIGHT
    reset_night_actions(state)
    reset_day_actions(state)
    state.sub_phase = SubPhase.NIGHT_WOLF
    state.pending_hunter_seat = None
    return "进入下一夜"


def _after_hunter_shoot(state: GameState, rng: random.Random) -> str:
    """猎人开枪结束后继续流程"""
    was_night = state.phase == Phase.NIGHT
    state.pending_hunter_seat = None

    winner = check_winner(state)
    if winner:
        _set_winner(state, winner)
        return f"对局结束，{winner.value} 胜"

    if was_night:
        state.phase = Phase.DAY
        state.day_number += 1
        reset_day_actions(state)
        state.sub_phase = SubPhase.DAY_ANNOUNCE
        return f"第 {state.day_number} 天开始"

    return _go_to_next_night(state, rng)
