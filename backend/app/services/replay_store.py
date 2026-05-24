"""复盘持久化：局终写入 JSON，重启后可读"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.game import GameState
from app.services.replay_view import build_game_replay

_REPLAY_DIR = Path(__file__).resolve().parents[1] / "data" / "replays"


def replay_dir() -> Path:
    d = Path(settings.replays_dir) if settings.replays_dir else _REPLAY_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(game_id: str) -> Path:
    return replay_dir() / f"{game_id}.json"


def _state_to_json(state: GameState) -> dict[str, Any]:
    data = state.model_dump(mode="json")
    data["alive_seats"] = sorted(state.alive_seats)
    return data


def _state_from_json(data: dict[str, Any]) -> GameState:
    raw = dict(data)
    raw["alive_seats"] = set(raw.get("alive_seats") or [])
    return GameState.model_validate(raw)


def save(game_id: str, state: GameState, human_seat: int, player_token: str) -> None:
    """局终落盘：完整 state + 复盘视图 + token（供鉴权）"""
    payload = {
        "game_id": game_id,
        "player_token": player_token,
        "human_seat": human_seat,
        "state": _state_to_json(state),
        "replay": build_game_replay(state, human_seat).model_dump(mode="json"),
    }
    _path(game_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_record(game_id: str) -> dict[str, Any] | None:
    p = _path(game_id)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_state(game_id: str) -> GameState | None:
    record = load_record(game_id)
    if record is None:
        return None
    return _state_from_json(record["state"])


def verify_token(game_id: str, token: str) -> bool:
    record = load_record(game_id)
    if record is None:
        return False
    return record.get("player_token") == token


def list_persisted_ids() -> list[str]:
    return sorted(p.stem for p in replay_dir().glob("*.json"))
