"""对局注册表（内存 + 复盘落盘读取）"""

from __future__ import annotations

import time

from app.game.engine import create_engine
from app.models.game import GameListItem, GameState, GameStatus, Phase


class GameRegistry:
    def __init__(self) -> None:
        self._games: dict[str, GameState] = {}
        self._tokens: dict[str, str] = {}
        self._human_seats: dict[str, int] = {}
        self._human_names: dict[str, str] = {}
        self._created_at: dict[str, float] = {}

    def create(
        self,
        game_id: str,
        player_name: str,
        player_token: str,
        seed: int | None = None,
        personality_library_id: str | None = None,
        strategy_library_id: str | None = None,
    ) -> tuple[GameState, int]:
        state = GameState(
            game_id=game_id,
            status=GameStatus.WAITING,
            phase=Phase.SETUP,
            players=[],
            alive_seats=set(),
            personality_library_id=personality_library_id or "default",
            strategy_library_id=strategy_library_id or "default",
        )
        engine = create_engine(state, seed)
        human_seat, _ = engine.setup(player_name, seed)
        state.status = GameStatus.IN_PROGRESS
        self._games[game_id] = state
        self._tokens[game_id] = player_token
        self._human_seats[game_id] = human_seat
        self._human_names[game_id] = player_name
        self._created_at[game_id] = time.time()
        return state, human_seat

    def get(self, game_id: str) -> GameState | None:
        return self._games.get(game_id)

    def get_engine(self, game_id: str):
        state = self.get(game_id)
        if state is None:
            return None
        return create_engine(state)

    def verify_token(self, game_id: str, token: str) -> bool:
        return self._tokens.get(game_id) == token

    def get_token(self, game_id: str) -> str | None:
        return self._tokens.get(game_id)

    def human_seat(self, game_id: str) -> int | None:
        return self._human_seats.get(game_id)

    def human_name(self, game_id: str) -> str:
        return self._human_names.get(game_id, "玩家")

    def list_games(self, in_progress_only: bool = False) -> list[GameListItem]:
        items: list[GameListItem] = []
        for game_id, state in self._games.items():
            if in_progress_only and state.phase == Phase.GAME_OVER:
                continue
            items.append(
                GameListItem(
                    game_id=game_id,
                    status=state.status,
                    phase=state.phase,
                    day_number=state.day_number,
                    human_player_name=self.human_name(game_id),
                    winner=state.winner,
                    created_at=self._created_at.get(game_id, 0.0),
                )
            )
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items


game_registry = GameRegistry()
