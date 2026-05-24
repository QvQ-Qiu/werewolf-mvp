"""规则引擎核心规则测试"""

import random

from app.game.engine import create_engine
from app.game.roles import resolve_night_deaths
from app.game.simulator import create_test_engine, find_seats_by_role
from app.game.voting import resolve_wolf_kill, tally_day_votes
from app.game.win_condition import check_winner
from app.models.actions import Action, ActionType
from app.models.game import (
    DayVoteRecord,
    Faction,
    GameState,
    NightActionBundle,
    Phase,
    Role,
    SubPhase,
    WitchState,
)
from app.game.dealing import setup_game


def _make_state(seed: int = 1) -> GameState:
    state = GameState(game_id="t", seed=seed, alive_seats=set())
    setup_game(state, "玩家", seed)
    return state


def test_wolf_vote_all_wolves_count() -> None:
    """三狼提名均计入票型，多数决出刀口"""
    state = _make_state(100)
    wolves = state.alive_wolves()
    assert len(wolves) == 3

    state.night_actions.wolf_nominations[wolves[0].seat] = 1
    state.night_actions.wolf_nominations[wolves[1].seat] = 2
    state.night_actions.wolf_nominations[wolves[2].seat] = 2

    target = resolve_wolf_kill(state, random.Random(0))
    assert target == 2


def test_wolf_vote_human_breaks_tie() -> None:
    """人类狼票与 AI 共同参与平票随机"""
    state = _make_state(102)
    wolves = state.alive_wolves()
    for w in wolves:
        w.is_human = False
    wolves[0].is_human = True

    state.night_actions.wolf_nominations[wolves[0].seat] = 3
    state.night_actions.wolf_nominations[wolves[1].seat] = 4
    state.night_actions.wolf_nominations[wolves[2].seat] = 4

    rng = random.Random(0)
    assert resolve_wolf_kill(state, rng) in {3, 4}


def test_wolf_vote_tie_random() -> None:
    """AI 狼平票随机选刀口"""
    state = _make_state(101)
  # 强制全部 AI（重新分配使 seat1 非狼）
    for p in state.players:
        p.is_human = False
    state.players[0].is_human = True

    wolves = state.alive_wolves()
    assert len(wolves) == 3
    targets = [3, 4, 5]
    for wolf, t in zip(wolves, targets):
        state.night_actions.wolf_nominations[wolf.seat] = t

    rng = random.Random(42)
    results = {resolve_wolf_kill(state, rng) for _ in range(20)}
    assert results.issubset({3, 4, 5})
    assert len(results) >= 2  # 随机应出现多个候选


def test_same_guard_heal_kill() -> None:
    """同守同救：仍死亡"""
    state = _make_state(200)
    state.wolf_kill_target = 5
    state.night_actions = NightActionBundle(
        witch_heal_target=5,
        guard_protect_target=5,
    )
    state.witch_state = WitchState(heal_available=True, poison_available=True)

    deaths = resolve_night_deaths(state)
    assert 5 in deaths


def test_guard_only_saves() -> None:
    """仅守护：存活"""
    state = _make_state(201)
    state.wolf_kill_target = 5
    state.night_actions = NightActionBundle(guard_protect_target=5)
    deaths = resolve_night_deaths(state)
    assert 5 not in deaths


def test_witch_heal_only_saves() -> None:
    """仅解药：存活"""
    state = _make_state(202)
    state.wolf_kill_target = 5
    state.night_actions = NightActionBundle(witch_heal_target=5)
    state.witch_state.heal_available = True
    deaths = resolve_night_deaths(state)
    assert 5 not in deaths


def test_witch_poison_kills() -> None:
    """女巫毒杀"""
    state = _make_state(203)
    state.wolf_kill_target = None
    state.night_actions = NightActionBundle(witch_poison_target=7)
    state.witch_state.poison_available = True
    deaths = resolve_night_deaths(state)
    assert 7 in deaths


def test_day_vote_tie() -> None:
    """平票无人出局"""
    state = _make_state(300)
    state.day_votes = [
        DayVoteRecord(voter_seat=1, target_seat=2),
        DayVoteRecord(voter_seat=2, target_seat=3),
        DayVoteRecord(voter_seat=3, target_seat=2),
        DayVoteRecord(voter_seat=4, target_seat=3),
    ]
    exiled, counts, is_tie = tally_day_votes(state)
    assert is_tie is True
    assert exiled is None


def test_day_vote_single_winner() -> None:
    state = _make_state(301)
    state.day_votes = [
        DayVoteRecord(voter_seat=1, target_seat=5),
        DayVoteRecord(voter_seat=2, target_seat=5),
        DayVoteRecord(voter_seat=3, target_seat=6),
    ]
    exiled, _, is_tie = tally_day_votes(state)
    assert is_tie is False
    assert exiled == 5


def test_hunter_shoot_after_night_kill() -> None:
    """猎人被狼刀杀可开枪"""
    engine = create_test_engine(seed=500)
    state = engine.state
    hunter_seat = find_seats_by_role(state, Role.HUNTER)[0]

    # 手动推进到夜结算
    state.night_actions.wolf_nominations = {w.seat: hunter_seat for w in state.alive_wolves()}
    state.sub_phase = SubPhase.NIGHT_RESOLVE
    state.wolf_kill_target = hunter_seat
    engine.advance_phase()  # 夜结算

    assert state.sub_phase == SubPhase.HUNTER_SHOOT
    assert state.pending_hunter_seat == hunter_seat

    victim = next(s for s in state.alive_seats if s != hunter_seat)
    result = engine.apply_action(
        Action(
            action_type=ActionType.HUNTER_SHOOT,
            actor_seat=hunter_seat,
            target_seat=victim,
        )
    )
    assert result.ok
    assert victim not in state.alive_seats


def test_hunter_cannot_shoot_when_poisoned() -> None:
    """被毒杀猎人不能开枪"""
    engine = create_test_engine(seed=501)
    state = engine.state
    hunter_seat = find_seats_by_role(state, Role.HUNTER)[0]

    state.wolf_kill_target = hunter_seat
    state.night_actions = NightActionBundle(
        wolf_nominations={w.seat: hunter_seat for w in state.alive_wolves()},
        witch_poison_target=hunter_seat,
    )
    state.witch_state.poison_available = True
    state.sub_phase = SubPhase.NIGHT_RESOLVE
    engine.advance_phase()

    assert state.sub_phase != SubPhase.HUNTER_SHOOT or state.pending_hunter_seat != hunter_seat


def test_win_village_all_wolves_dead() -> None:
    state = _make_state(600)
    for p in state.players:
        if p.role == Role.WOLF:
            p.is_alive = False
            state.alive_seats.discard(p.seat)
    assert check_winner(state) == Faction.VILLAGE


def test_win_wolf_tu_bian_gods_dead() -> None:
    """狼屠边：神职全灭"""
    state = _make_state(601)
    for p in state.players:
        if p.role in {Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD}:
            p.is_alive = False
            state.alive_seats.discard(p.seat)
    assert check_winner(state) == Faction.WOLF


def test_win_wolf_tu_bian_villagers_dead() -> None:
    """狼屠边：村民全灭（神职仍在）"""
    state = _make_state(603)
    for p in state.players:
        if p.role == Role.VILLAGER:
            p.is_alive = False
            state.alive_seats.discard(p.seat)
    assert len(state.alive_gods()) > 0
    assert check_winner(state) == Faction.WOLF


def test_win_not_wolf_by_count_only() -> None:
    """仅狼人数>=神职但两侧都未屠边时不判狼胜"""
    state = _make_state(604)
    # 默认 10 人局：3 狼 4 民 4 神，不改动存活
    assert check_winner(state) is None


def test_win_village_priority_when_both() -> None:
    """同时达成时好人胜（狼全灭优先）"""
    state = _make_state(602)
    for p in state.players:
        p.is_alive = False
    state.alive_seats = set()
    assert check_winner(state) == Faction.VILLAGE


def test_witch_one_potion_per_night() -> None:
    """每夜最多使用一瓶药水"""
    engine = create_test_engine(seed=710)
    state = engine.state
    witch = find_seats_by_role(state, Role.WITCH)[0]
    state.sub_phase = SubPhase.NIGHT_WITCH
    state.wolf_kill_target = 5
    state.night_actions.wolf_nominations = {w.seat: 5 for w in state.alive_wolves()}

    heal = engine.apply_action(
        Action(action_type=ActionType.WITCH_HEAL, actor_seat=witch, target_seat=5)
    )
    assert heal.ok

    poison = engine.apply_action(
        Action(action_type=ActionType.WITCH_POISON, actor_seat=witch, target_seat=7)
    )
    assert not poison.ok
    assert "每夜最多使用一瓶药水" in poison.message


def test_witch_poison_consumes_potion() -> None:
    engine = create_test_engine(seed=711)
    state = engine.state
    witch = find_seats_by_role(state, Role.WITCH)[0]
    state.sub_phase = SubPhase.NIGHT_WITCH

    result = engine.apply_action(
        Action(action_type=ActionType.WITCH_POISON, actor_seat=witch, target_seat=7)
    )
    assert result.ok
    assert state.witch_state.poison_available is False


def test_witch_poison_with_wolf_kill() -> None:
    """女巫毒杀与狼刀同时生效"""
    state = _make_state(204)
    state.wolf_kill_target = 5
    state.night_actions = NightActionBundle(witch_poison_target=7)
    state.witch_state.poison_available = False  # 已在女巫阶段消耗
    deaths = resolve_night_deaths(state)
    assert 5 in deaths
    assert 7 in deaths


def test_witch_heal_peaceful_night() -> None:
    """女巫救狼刀目标：平安夜"""
    state = _make_state(205)
    state.wolf_kill_target = 5
    state.night_actions = NightActionBundle(witch_heal_target=5)
    state.witch_state.heal_available = False
    deaths = resolve_night_deaths(state)
    assert deaths == []


def test_witch_poison_not_cleared_when_potion_used() -> None:
    """毒药已消耗时 resolve 仍应计入毒杀（修复平安夜 bug）"""
    state = _make_state(206)
    state.wolf_kill_target = None
    state.night_actions = NightActionBundle(witch_poison_target=3)
    state.witch_state.poison_available = False
    deaths = resolve_night_deaths(state)
    assert 3 in deaths


def test_guard_after_witch_order() -> None:
    """守卫在女巫之后：仅守护可挡狼刀"""
    state = _make_state(207)
    state.wolf_kill_target = 4
    state.night_actions = NightActionBundle(guard_protect_target=4)
    deaths = resolve_night_deaths(state)
    assert 4 not in deaths


def test_announce_night_deaths_after_resolve() -> None:
    """死讯公布在夜结算时完成，有死亡时不应出现平安夜"""
    engine = create_test_engine(seed=720)
    state = engine.state
    victim = next(s for s in state.alive_seats)

    state.night_actions.wolf_nominations = {w.seat: victim for w in state.alive_wolves()}
    state.night_actions.guard_done = True
    state.night_actions.witch_done = True
    state.sub_phase = SubPhase.NIGHT_RESOLVE
    state.wolf_kill_target = victim
    engine.advance_phase()

    assert victim in state.last_night_deaths
    assert not any("平安夜" in e.content for e in state.public_log)


def test_guard_blocks_wolf_via_engine() -> None:
    """守卫守护刀口：夜结算后目标存活"""
    engine = create_test_engine(seed=721)
    state = engine.state
    guard = find_seats_by_role(state, Role.GUARD)[0]
    victim = next(s for s in state.alive_seats if s != guard)

    state.night_actions.wolf_nominations = {w.seat: victim for w in state.alive_wolves()}
    state.sub_phase = SubPhase.NIGHT_GUARD
    state.wolf_kill_target = victim
    engine.apply_action(
        Action(action_type=ActionType.GUARD_PROTECT, actor_seat=guard, target_seat=victim)
    )
    engine.advance_phase()

    assert victim not in state.last_night_deaths
    assert victim in state.alive_seats


def test_guard_cannot_protect_same_two_nights() -> None:
    engine = create_test_engine(seed=700)
    state = engine.state
    guard = find_seats_by_role(state, Role.GUARD)[0]
    state.sub_phase = SubPhase.NIGHT_GUARD
    state.guard_last_target = 3

    result = engine.apply_action(
        Action(action_type=ActionType.GUARD_PROTECT, actor_seat=guard, target_seat=3)
    )
    assert not result.ok
