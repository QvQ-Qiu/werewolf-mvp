"""完整一局模拟测试"""

import random

from app.game.simulator import create_test_engine, run_until_end
from app.models.game import Phase, Role


def test_full_game_simulation() -> None:
    """固定种子跑完一整局"""
    engine = create_test_engine(seed=2024)
    rng = random.Random(2024)
    final = run_until_end(engine, rng, max_rounds=30)

    assert final.phase == Phase.GAME_OVER
    assert final.winner is not None
    assert len(final.public_log) > 0


def test_full_game_completes_within_time() -> None:
    """模拟应在合理步数内结束"""
    engine = create_test_engine(seed=8888)
    rng = random.Random(8888)
    run_until_end(engine, rng, max_rounds=50)
    assert engine.state.phase == Phase.GAME_OVER


def test_simulation_has_valid_end_state() -> None:
    engine = create_test_engine(seed=31415)
    run_until_end(engine, random.Random(31415))
    state = engine.state

    wolves_alive = sum(1 for p in state.players if p.is_alive and p.role == Role.WOLF)
    if state.winner.value == "village":
        assert wolves_alive == 0
    elif state.winner.value == "wolf":
        gods = state.alive_gods()
        wolves = [p for p in state.players if p.is_alive and p.role == Role.WOLF]
        assert len(wolves) >= len(gods)
