"""WebSocket 与 GameLoop 集成测试"""

import time

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def _create_game(seed: int = 42) -> dict:
    res = client.post("/games", json={"player_name": "WS测试", "seed": seed})
    assert res.status_code == 200
    return res.json()


def _villager_seed() -> int:
    """返回人类为村民的 seed（便于 Mock AI 全自动推进）"""
    for seed in range(100):
        data = _create_game(seed=seed)
        if data["human_role"] == "villager":
            return seed
    return 42


def test_websocket_connect_and_game_started() -> None:
    data = _create_game()
    game_id = data["game_id"]
    token = data["player_token"]

    with client.websocket_connect(f"/ws/games/{game_id}?token={token}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "CONNECTED"

        started = ws.receive_json()
        assert started["type"] == "GAME_STARTED"
        assert started["payload"]["your_seat"] == data["human_seat"]
        assert started["payload"]["your_role"] == data["human_role"]
        assert len(started["payload"]["players"]) == 10

        events = []
        for _ in range(5):
            try:
                msg = ws.receive_json()
                events.append(msg["type"])
            except Exception:
                break

        assert "PHASE_CHANGED" in events or "STATE_SNAPSHOT" in events


def test_websocket_invalid_token() -> None:
    data = _create_game()
    with client.websocket_connect(f"/ws/games/{data['game_id']}?token=bad") as ws:
        err = ws.receive_json()
        assert err["type"] == "ERROR"
        assert err["payload"]["code"] == "UNAUTHORIZED"


def test_websocket_ping_pong() -> None:
    data = _create_game()
    with client.websocket_connect(
        f"/ws/games/{data['game_id']}?token={data['player_token']}"
    ) as ws:
        ws.send_json({"type": "PING", "payload": {}})
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "PONG":
                break
        else:
            pytest.fail("未收到 PONG")


def test_get_game_includes_players() -> None:
    data = _create_game()
    res = client.get(f"/games/{data['game_id']}")
    assert res.status_code == 200
    body = res.json()
    assert len(body["players"]) == 10
    assert body["phase"] == "night"


def test_mock_ai_advances_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock AI 应能推进至白天（人类为村民时无需夜晚输入）"""
    monkeypatch.setattr(settings, "game_speech_max_seconds", 1)
    monkeypatch.setattr(settings, "game_night_action_timeout_seconds", 0.5)

    seed = _villager_seed()
    data = _create_game(seed=seed)
    assert data["human_role"] == "villager"

    game_id = data["game_id"]
    token = data["player_token"]

    with client.websocket_connect(f"/ws/games/{game_id}?token={token}") as ws:
        seen_phases: set[str] = set()
        deadline = time.time() + 45

        while time.time() < deadline:
            try:
                msg = ws.receive_json()
            except Exception:
                break
            if msg["type"] == "PHASE_CHANGED":
                seen_phases.add(msg["payload"]["phase"])
            if msg["type"] == "GAME_END":
                break
            if "day" in seen_phases:
                break

        assert "day" in seen_phases or "game_over" in seen_phases
