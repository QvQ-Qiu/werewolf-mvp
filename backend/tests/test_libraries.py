"""人格库 / 策略库 API 与存储"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import library_store

client = TestClient(app)


def test_list_builtin_personality_library() -> None:
    res = client.get("/libraries/personalities")
    assert res.status_code == 200
    items = res.json()
    assert any(x["id"] == "default" and x["is_builtin"] for x in items)


def test_create_and_use_personality_library() -> None:
    created = client.post(
        "/libraries/personalities",
        json={"name": "测试人格库", "fork_from": "default"},
    )
    assert created.status_code == 201
    lib_id = created.json()["id"]
    assert len(created.json()["personalities"]) >= 9

    got = client.get(f"/libraries/personalities/{lib_id}")
    assert got.status_code == 200

    game = client.post(
        "/games",
        json={
            "player_name": "测试",
            "seed": 1,
            "personality_library_id": lib_id,
            "strategy_library_id": "default",
        },
    )
    assert game.status_code == 200

    client.delete(f"/libraries/personalities/{lib_id}")


def test_builtin_personality_library_protected() -> None:
    assert client.put("/libraries/personalities/default", json={"name": "x"}).status_code == 403
    assert client.delete("/libraries/personalities/default").status_code == 403


def test_strategy_library_fork_and_patch() -> None:
    forked = client.post(
        "/libraries/strategies",
        json={"name": "延续库", "fork_from": "default"},
    )
    assert forked.status_code == 201
    lib_id = forked.json()["id"]

    patched = client.patch(
        f"/libraries/strategies/{lib_id}",
        json={
            "append_by_role": {
                "wolf": [
                    {
                        "id": "W99",
                        "role": "wolf",
                        "name": "自定义狼策",
                        "tendency": "aggressive",
                        "priority": 3,
                        "weight": 1.0,
                        "prompt_hint": "测试",
                    }
                ]
            }
        },
    )
    assert patched.status_code == 200
    wolves = patched.json()["strategies_by_role"]["wolf"]
    assert any(s["id"] == "W99" for s in wolves)

    client.delete(f"/libraries/strategies/{lib_id}")


def test_builtin_strategy_library_protected() -> None:
    assert client.put("/libraries/strategies/default", json={"name": "x"}).status_code == 403
    assert client.patch("/libraries/strategies/default", json={"append_by_role": {}}).status_code == 403
    assert client.delete("/libraries/strategies/default").status_code == 403


def test_resolve_templates_default() -> None:
    templates = library_store.resolve_personality_templates("default")
    assert len(templates) >= 9
