"""夜晚子阶段顺序与结算集成测试"""

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.orchestrator import _submit_witch
from app.game.engine import create_engine
from app.game.dealing import setup_game
from app.game.night_resolution import build_night_death_reasons, ensure_wolf_kill_target
from app.game.roles import resolve_night_deaths
from app.game.simulator import find_seats_by_role
from app.game.state_machine import advance_sub_phase, NIGHT_FLOW
from app.game.voting import resolve_wolf_kill
from app.models.game import GameState, NightActionBundle, Role, SubPhase, WitchState


def _make_state(seed: int = 42) -> GameState:
    state = GameState(game_id="night-flow", seed=seed, alive_seats=set())
    setup_game(state, "玩家", seed)
    return state


def test_night_flow_sub_phase_order() -> None:
    assert [s.value for s in NIGHT_FLOW] == [
        "night_wolf",
        "night_seer",
        "night_witch",
        "night_guard",
        "night_resolve",
    ]


def test_full_night_wolf_kills_3_witch_heals_1_guard_1() -> None:
    """狼刀 3，女巫救 1（无效），守卫守 1：仅 3 号死于狼刀。"""
    state = _make_state(77)
    rng = random.Random(77)
    wolves = state.alive_wolves()
    victim = 3
    for w in wolves:
        state.night_actions.wolf_nominations[w.seat] = victim

    state.wolf_kill_target = resolve_wolf_kill(state, rng)
    assert state.wolf_kill_target == victim

    state.night_actions.witch_heal_target = 1
    state.night_actions.guard_protect_target = 1
    state.witch_state = WitchState(heal_available=False, poison_available=True)

    deaths = resolve_night_deaths(state)
    assert deaths == [victim]

    reasons = build_night_death_reasons(state, deaths)
    assert reasons[victim] == "狼刀"


def test_full_night_same_guard_heal_still_dies() -> None:
    """狼刀 5，同守同救：仍死于狼刀（规则特例）。"""
    state = _make_state(88)
    target = 5
    state.wolf_kill_target = target
    state.night_actions = NightActionBundle(
        witch_heal_target=target,
        guard_protect_target=target,
    )
    state.witch_state.heal_available = False

    deaths = resolve_night_deaths(state)
    assert deaths == [target]
    reasons = build_night_death_reasons(state, deaths)
    assert reasons[target] == "狼刀（同守同救）"


def test_ensure_wolf_kill_on_seer_phase_entry() -> None:
    """狼刀在离开 night_wolf 进入 night_seer 时结算，而非预言家之后。"""
    state = _make_state(99)
    rng = random.Random(99)
    state.sub_phase = SubPhase.NIGHT_WOLF
    wolves = state.alive_wolves()
    for w in wolves:
        state.night_actions.wolf_nominations[w.seat] = 4

    msg = advance_sub_phase(state, rng)
    assert state.sub_phase == SubPhase.NIGHT_SEER
    assert state.wolf_kill_target == 4
    assert "night_seer" in msg


def test_wolf_kill_not_deferred_past_seer() -> None:
    """进入 night_seer 后狼刀应已确定，进入 night_witch 不再变更。"""
    state = _make_state(101)
    rng = random.Random(101)
    state.sub_phase = SubPhase.NIGHT_WOLF
    wolves = state.alive_wolves()
    for w in wolves:
        state.night_actions.wolf_nominations[w.seat] = 5

    advance_sub_phase(state, rng)
    assert state.sub_phase == SubPhase.NIGHT_SEER
    kill_at_seer = state.wolf_kill_target

    state.night_actions.seer_check_target = 2
    advance_sub_phase(state, rng)
    assert state.sub_phase == SubPhase.NIGHT_WITCH
    assert state.wolf_kill_target == kill_at_seer


def test_night_sub_phases_advance_one_step_at_a_time() -> None:
    """advance_sub_phase 每次只推进一个夜晚子阶段。"""
    state = _make_state(55)
    rng = random.Random(55)
    assert state.sub_phase == SubPhase.NIGHT_WOLF

    wolves = state.alive_wolves()
    for w in wolves:
        state.night_actions.wolf_nominations[w.seat] = 3

    advance_sub_phase(state, rng)
    assert state.sub_phase == SubPhase.NIGHT_SEER

    seer = find_seats_by_role(state, Role.SEER)[0]
    state.night_actions.seer_check_target = seer
    advance_sub_phase(state, rng)
    assert state.sub_phase == SubPhase.NIGHT_WITCH


@pytest.mark.asyncio
async def test_witch_heal_wrong_target_single_llm() -> None:
    state = _make_state(56)
    engine = create_engine(state)
    witch = find_seats_by_role(state, Role.WITCH)[0]
    wolves = state.alive_wolves()
    for w in wolves:
        state.night_actions.wolf_nominations[w.seat] = 3
    state.sub_phase = SubPhase.NIGHT_WITCH
    ensure_wolf_kill_target(state, engine.rng)

    mock_pipe = MagicMock()
    mock_pipe.run_night_action_pipeline = AsyncMock(
        return_value={"action_type": "witch_heal", "target_seat": 1, "extra": {}}
    )

    with patch("app.ai.orchestrator.is_llm_enabled", return_value=True), patch(
        "app.ai.orchestrator._use_night_fast", return_value=True
    ):
        await _submit_witch(engine, mock_pipe)

    assert state.night_actions.witch_done
    assert mock_pipe.run_night_action_pipeline.await_count == 1
