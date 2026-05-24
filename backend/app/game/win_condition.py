"""胜负判定（标准屠边）"""

from app.models.game import Faction, GameState, Role


def _alive_villagers(state: GameState) -> list:
    return [p for p in state.players if p.is_alive and p.role == Role.VILLAGER]


def _alive_good_players(state: GameState) -> list:
    """好人 = 所有非狼存活玩家（神职 + 村民）"""
    return [p for p in state.players if p.is_alive and p.role != Role.WOLF]


def check_winner(state: GameState) -> Faction | None:
    """
    屠边胜负判定：
    - 好人阵营胜：所有狼人出局
    - 狼人胜（至少一匹狼存活）且满足其一：
        · 场上没有村民
        · 场上没有神职
        · 场上没有好人（非狼全灭）
    """
    alive_wolves = [p for p in state.players if p.is_alive and p.role == Role.WOLF]

    if len(alive_wolves) == 0:
        return Faction.VILLAGE

    if len(alive_wolves) > 0:
        villagers = _alive_villagers(state)
        gods = state.alive_gods()
        good_players = _alive_good_players(state)

        if len(villagers) == 0 or len(gods) == 0 or len(good_players) == 0:
            return Faction.WOLF

    return None
