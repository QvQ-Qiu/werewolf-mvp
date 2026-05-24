"""发牌测试"""

from collections import Counter

from app.game.dealing import ROLE_DECK, deal_roles, setup_game
from app.game.simulator import create_test_engine
from app.models.game import GameState, Phase, Role, SubPhase


def test_role_deck_composition() -> None:
    assert len(ROLE_DECK) == 10
    counts = Counter(ROLE_DECK)
    assert counts[Role.WOLF] == 3
    assert counts[Role.SEER] == 1
    assert counts[Role.WITCH] == 1
    assert counts[Role.HUNTER] == 1
    assert counts[Role.GUARD] == 1
    assert counts[Role.VILLAGER] == 3


def test_deal_roles_length_and_composition() -> None:
    roles = deal_roles(seed=123)
    assert len(roles) == 10
    assert Counter(roles) == Counter(ROLE_DECK)


def test_setup_game_ten_players() -> None:
    engine = create_test_engine(seed=99)
    state = engine.state
    assert len(state.players) == 10
    assert len(state.alive_seats) == 10
    assert state.phase == Phase.NIGHT
    assert state.sub_phase == SubPhase.NIGHT_WOLF
    assert state.day_number == 0
    assert Counter(p.role for p in state.players) == Counter(ROLE_DECK)


def test_setup_reproducible_with_seed() -> None:
    s1 = GameState(game_id="a", seed=0, alive_seats=set())
    s2 = GameState(game_id="b", seed=0, alive_seats=set())
    setup_game(s1, "玩家", seed=777)
    setup_game(s2, "玩家", seed=777)
    roles1 = [p.role for p in s1.players]
    roles2 = [p.role for p in s2.players]
    assert roles1 == roles2
