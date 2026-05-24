"""健康检查测试"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_game() -> None:
    response = client.post("/games", json={"player_name": "测试玩家", "seed": 42})
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert "ws_url" in data
    assert "player_token" in data
    assert "human_seat" in data
    assert "human_role" in data
    assert 1 <= data["human_seat"] <= 10
