"""无 AI 自动对局模拟（测试与脚本复用）"""

from __future__ import annotations

import random
from typing import Callable

from app.game.engine import RuleEngine, create_engine
from app.models.actions import Action, ActionType
from app.models.game import GameState, Phase, Role, SubPhase
from app.game.roles import find_role_seat


def find_seats_by_role(state: GameState, role: Role, alive_only: bool = True) -> list[int]:
    return [
        p.seat
        for p in state.players
        if p.role == role and (not alive_only or p.is_alive)
    ]


def pick_vote_target(state: GameState, voter_seat: int, rng: random.Random) -> int | None:
    """简单投票策略：随机投一名存活玩家（可弃票）"""
    candidates = [s for s in state.alive_seats if s != voter_seat]
    if not candidates:
        return None
    if rng.random() < 0.1:
        return None
    return rng.choice(candidates)


def complete_night_wolf(engine: RuleEngine, rng: random.Random) -> None:
    state = engine.state
    wolf_seats = {w.seat for w in state.alive_wolves()}
    candidates = [s for s in sorted(state.alive_seats) if s not in wolf_seats]
    if not candidates:
        engine.advance_phase()
        return
    for wolf in state.alive_wolves():
        target = rng.choice(candidates)
        engine.apply_action(
            Action(
                action_type=ActionType.WOLF_NOMINATE,
                actor_seat=wolf.seat,
                target_seat=target,
            )
        )
    engine.advance_phase()


def complete_night_seer(engine: RuleEngine, rng: random.Random) -> None:
    state = engine.state
    seer = find_role_seat(state, Role.SEER)
    if seer and seer in state.alive_seats:
        candidates = sorted(state.alive_seats)
        target = rng.choice(candidates)
        engine.apply_action(
            Action(action_type=ActionType.SEER_CHECK, actor_seat=seer, target_seat=target)
        )
    engine.advance_phase()


def complete_night_witch(
    engine: RuleEngine,
    rng: random.Random,
    heal: bool = False,
    poison: bool = False,
    poison_target: int | None = None,
) -> None:
    state = engine.state
    witch = find_role_seat(state, Role.WITCH)
    if witch and witch in state.alive_seats:
        from app.game.voting import resolve_wolf_kill

        if state.wolf_kill_target is None:
            state.wolf_kill_target = resolve_wolf_kill(state, rng)
        if heal and state.witch_state.heal_available and state.wolf_kill_target:
            engine.apply_action(
                Action(
                    action_type=ActionType.WITCH_HEAL,
                    actor_seat=witch,
                    target_seat=state.wolf_kill_target,
                )
            )
        if poison and state.witch_state.poison_available:
            target = poison_target or rng.choice(sorted(state.alive_seats))
            engine.apply_action(
                Action(
                    action_type=ActionType.WITCH_POISON,
                    actor_seat=witch,
                    target_seat=target,
                )
            )
        engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=witch))
    engine.advance_phase()


def complete_night_guard(engine: RuleEngine, rng: random.Random) -> None:
    state = engine.state
    guard = find_role_seat(state, Role.GUARD)
    if guard and guard in state.alive_seats:
        candidates = [s for s in state.alive_seats if s != state.guard_last_target]
        if candidates:
            target = rng.choice(candidates)
            engine.apply_action(
                Action(
                    action_type=ActionType.GUARD_PROTECT,
                    actor_seat=guard,
                    target_seat=target,
                )
            )
        else:
            engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=guard))
    engine.advance_phase()


def complete_hunter_if_needed(
    engine: RuleEngine, rng: random.Random, shoot: bool = True
) -> None:
    state = engine.state
    if state.sub_phase != SubPhase.HUNTER_SHOOT or state.pending_hunter_seat is None:
        return
    hunter = state.pending_hunter_seat
    if shoot:
        targets = [s for s in state.alive_seats if s != hunter]
        if targets:
            target = rng.choice(targets)
            engine.apply_action(
                Action(
                    action_type=ActionType.HUNTER_SHOOT,
                    actor_seat=hunter,
                    target_seat=target,
                )
            )
            return
    engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=hunter))


def complete_night(engine: RuleEngine, rng: random.Random, **witch_kw) -> None:
    """完成一整夜（含结算与猎人开枪）"""
    while engine.state.phase == Phase.NIGHT and engine.state.phase != Phase.GAME_OVER:
        sub = engine.state.sub_phase
        if sub == SubPhase.NIGHT_WOLF:
            complete_night_wolf(engine, rng)
        elif sub == SubPhase.NIGHT_SEER:
            complete_night_seer(engine, rng)
        elif sub == SubPhase.NIGHT_WITCH:
            complete_night_witch(engine, rng, **witch_kw)
        elif sub == SubPhase.NIGHT_GUARD:
            complete_night_guard(engine, rng)
        elif sub == SubPhase.NIGHT_RESOLVE:
            engine.advance_phase()
        elif sub == SubPhase.HUNTER_SHOOT:
            complete_hunter_if_needed(engine, rng)
        else:
            break


def complete_day(engine: RuleEngine, rng: random.Random) -> None:
    """完成一整日"""
    while engine.state.phase == Phase.DAY and engine.state.phase != Phase.GAME_OVER:
        sub = engine.state.sub_phase
        if sub == SubPhase.DAY_ANNOUNCE:
            engine.advance_phase()
        elif sub == SubPhase.DAY_SPEECH:
            state = engine.state
            while state.current_speaker_index < len(state.speech_order):
                seat = state.speech_order[state.current_speaker_index]
                engine.apply_action(
                    Action(
                        action_type=ActionType.SPEECH,
                        actor_seat=seat,
                        content=f"{seat}号发言",
                    )
                )
            engine.advance_phase()
        elif sub == SubPhase.DAY_VOTE:
            for seat in sorted(engine.state.alive_seats):
                target = pick_vote_target(engine.state, seat, rng)
                engine.apply_action(
                    Action(
                        action_type=ActionType.VOTE,
                        actor_seat=seat,
                        target_seat=target,
                    )
                )
            engine.advance_phase()
        elif sub == SubPhase.DAY_RESOLVE:
            engine.advance_phase()
        elif sub == SubPhase.HUNTER_SHOOT:
            complete_hunter_if_needed(engine, rng)
        else:
            break


def run_until_end(
    engine: RuleEngine,
    rng: random.Random | None = None,
    max_rounds: int = 20,
    on_night: Callable[[RuleEngine], None] | None = None,
    on_day: Callable[[RuleEngine], None] | None = None,
) -> GameState:
    """自动推进直至对局结束"""
    rng = rng or engine.rng
    for _ in range(max_rounds):
        if engine.state.phase == Phase.GAME_OVER:
            break
        if engine.state.phase == Phase.NIGHT:
            if on_night:
                on_night(engine)
            else:
                complete_night(engine, rng)
        elif engine.state.phase == Phase.DAY:
            if on_day:
                on_day(engine)
            else:
                complete_day(engine, rng)
        else:
            break
    return engine.state


def create_test_engine(seed: int = 42, player_name: str = "测试玩家") -> RuleEngine:
    state = GameState(game_id="test", seed=seed, alive_seats=set())
    engine = create_engine(state, seed)
    engine.setup(player_name, seed)
    return engine
