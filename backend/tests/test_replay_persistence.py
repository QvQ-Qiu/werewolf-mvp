"""复盘持久化与鉴权"""

from fastapi.testclient import TestClient

from app.main import app
from app.services import replay_store
from app.services.game_registry import game_registry
from app.models.game import Faction, GameStatus, Phase

client = TestClient(app)


def test_replay_persist_and_load_after_registry_clear() -> None:
    r = client.post("/games", json={"player_name": "复盘测试", "seed": 1})
    assert r.status_code == 200
    data = r.json()
    game_id = data["game_id"]
    token = data["player_token"]

    state = game_registry.get(game_id)
    assert state is not None
    state.phase = Phase.GAME_OVER
    state.status = GameStatus.FINISHED
    state.winner = Faction.VILLAGE
    human_seat = game_registry.human_seat(game_id) or 1
    replay_store.save(game_id, state, human_seat, token)

    game_registry._games.pop(game_id, None)

    bad = client.get(f"/games/{game_id}/replay", params={"token": "wrong"})
    assert bad.status_code == 403

    ok = client.get(f"/games/{game_id}/replay", params={"token": token})
    assert ok.status_code == 200
    body = ok.json()
    assert body["game_id"] == game_id
    assert body["winner"] == "village"
    assert len(body["players"]) == 10


def test_list_games() -> None:
    client.post("/games", json={"player_name": "列表测试"})
    r = client.get("/games")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_seat_traces() -> None:
    r = client.post("/games", json={"player_name": "追溯", "seed": 2})
    game_id = r.json()["game_id"]
    token = r.json()["player_token"]
    state = game_registry.get(game_id)
    assert state is not None
    from app.models.game import LlmTrace
    from datetime import datetime

    state.llm_traces.append(
        LlmTrace(
            player_seat=1,
            step="select_strategy",
            strategy_id="TEST",
            phase_ref="day1_night",
            prompt_summary="abc",
            response_summary="resp",
            messages_full=[{"role": "user", "content": "hi"}],
            timestamp=datetime.utcnow(),
        )
    )
    replay_store.save(game_id, state, 1, token)
    game_registry._games.pop(game_id, None)

    tr = client.get(f"/games/{game_id}/traces/1", params={"token": token})
    assert tr.status_code == 200
    assert tr.json()["traces"][0]["messages_full"]
