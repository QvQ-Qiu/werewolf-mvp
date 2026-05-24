"""发牌与座位分配"""

import random
from typing import Optional

from app.ai.personality import assign_personalities_to_ai
from app.models.game import GameState, GameStatus, NightActionBundle, Phase, Player, Role, SubPhase

# 固定 10 人板：3 狼、1 预、1 女、1 猎、1 守、3 民（合计 10 人）
ROLE_DECK: list[Role] = [
    Role.WOLF,
    Role.WOLF,
    Role.WOLF,
    Role.SEER,
    Role.WITCH,
    Role.HUNTER,
    Role.GUARD,
    Role.VILLAGER,
    Role.VILLAGER,
    Role.VILLAGER,
]


def deal_roles(seed: int) -> list[Role]:
    """随机洗牌发牌，返回与座位 1-10 对应的角色列表"""
    rng = random.Random(seed)
    roles = ROLE_DECK.copy()
    rng.shuffle(roles)
    return roles


def setup_game(
    state: GameState,
    player_name: str,
    seed: Optional[int] = None,
) -> tuple[int, Role]:
    """
    初始化 10 人局：随机分配座位与身份，人类随机占 1 席。
    返回 (人类座位, 人类角色)。
    """
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
    state.seed = seed
    rng = random.Random(seed)

    # 人类随机占 1～10 号座位
    human_seat = rng.randint(1, 10)
    roles = deal_roles(seed)

    players: list[Player] = []
    human_role: Optional[Role] = None
    for seat in range(1, 11):
        role = roles[seat - 1]
        if seat == human_seat:
            players.append(
                Player(seat=seat, name=player_name, is_human=True, role=role)
            )
            human_role = role
        else:
            players.append(
                Player(seat=seat, name=f"AI-{seat}", is_human=False, role=role)
            )

    state.players = players
    state.alive_seats = set(range(1, 11))
    state.status = GameStatus.IN_PROGRESS
    state.phase = Phase.NIGHT
    state.sub_phase = SubPhase.NIGHT_WOLF
    state.day_number = 0
    state.night_actions = NightActionBundle()

    assign_personalities_to_ai(state, rng)

    assert human_role is not None
    return human_seat, human_role
