"""人格库 / 策略库持久化（内置 default + 用户库 JSON 文件）"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.models.game import Role

_BUILTIN_ID = "default"
_BUILTIN_DISPLAY_NAME = "基础库"
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_BUILTIN_PERSONALITIES = _BACKEND_ROOT / "data" / "personalities.json"
_BUILTIN_STRATEGIES_DIR = _BACKEND_ROOT / "data" / "strategies"
_USER_LIBRARIES_ROOT = _BACKEND_ROOT / "data" / "user_libraries"
_USER_PERSONALITIES_DIR = _USER_LIBRARIES_ROOT / "personalities"
_USER_STRATEGIES_DIR = _USER_LIBRARIES_ROOT / "strategies"

_ROLE_FILES = {
    Role.WOLF: "wolf.json",
    Role.SEER: "seer.json",
    Role.WITCH: "witch.json",
    Role.HUNTER: "hunter.json",
    Role.GUARD: "guard.json",
    Role.VILLAGER: "villager.json",
}
_ROLE_VALUES = {r.value for r in _ROLE_FILES}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_user_dirs() -> None:
    _USER_PERSONALITIES_DIR.mkdir(parents=True, exist_ok=True)
    _USER_STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)


def user_libraries_root() -> Path:
    return _USER_LIBRARIES_ROOT


def load_builtin_personalities() -> list[dict[str, Any]]:
    with open(_BUILTIN_PERSONALITIES, encoding="utf-8") as f:
        data = json.load(f)
    return list(data["personalities"])


def load_builtin_strategies_by_role() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for role, filename in _ROLE_FILES.items():
        path = _BUILTIN_STRATEGIES_DIR / filename
        with open(path, encoding="utf-8") as f:
            out[role.value] = list(json.load(f))
    return out


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _reject_builtin_mutation(library_id: str, *, op: str) -> None:
    if library_id == _BUILTIN_ID:
        raise HTTPException(status_code=403, detail=f"基础库（{_BUILTIN_ID}）不可{op}")


def _personality_path(library_id: str) -> Path:
    _reject_builtin_mutation(library_id, op="写入")
    return _USER_PERSONALITIES_DIR / f"{library_id}.json"


def _strategy_path(library_id: str) -> Path:
    _reject_builtin_mutation(library_id, op="写入")
    return _USER_STRATEGIES_DIR / f"{library_id}.json"


def list_personality_libraries() -> list[dict[str, Any]]:
    _ensure_user_dirs()
    items: list[dict[str, Any]] = [
        {
            "id": _BUILTIN_ID,
            "name": _BUILTIN_DISPLAY_NAME,
            "is_builtin": True,
            "personality_count": len(load_builtin_personalities()),
            "updated_at": None,
        }
    ]
    for path in sorted(_USER_PERSONALITIES_DIR.glob("*.json")):
        data = _read_json(path)
        items.append(
            {
                "id": data["id"],
                "name": data.get("name", data["id"]),
                "is_builtin": False,
                "personality_count": len(data.get("personalities", [])),
                "updated_at": data.get("updated_at"),
            }
        )
    return items


def list_strategy_libraries() -> list[dict[str, Any]]:
    _ensure_user_dirs()
    builtin = load_builtin_strategies_by_role()
    items: list[dict[str, Any]] = [
        {
            "id": _BUILTIN_ID,
            "name": _BUILTIN_DISPLAY_NAME,
            "is_builtin": True,
            "strategy_role_count": len(builtin),
            "updated_at": None,
        }
    ]
    for path in sorted(_USER_STRATEGIES_DIR.glob("*.json")):
        data = _read_json(path)
        by_role = data.get("strategies_by_role", {})
        items.append(
            {
                "id": data["id"],
                "name": data.get("name", data["id"]),
                "is_builtin": False,
                "strategy_role_count": len(by_role),
                "updated_at": data.get("updated_at"),
            }
        )
    return items


def get_personality_library(library_id: str) -> dict[str, Any]:
    if library_id == _BUILTIN_ID:
        return {
            "id": _BUILTIN_ID,
            "name": _BUILTIN_DISPLAY_NAME,
            "is_builtin": True,
            "personalities": load_builtin_personalities(),
            "created_at": None,
            "updated_at": None,
        }
    path = _USER_PERSONALITIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="人格库不存在")
    return _read_json(path)


def get_strategy_library(library_id: str) -> dict[str, Any]:
    if library_id == _BUILTIN_ID:
        return {
            "id": _BUILTIN_ID,
            "name": _BUILTIN_DISPLAY_NAME,
            "is_builtin": True,
            "strategies_by_role": load_builtin_strategies_by_role(),
            "created_at": None,
            "updated_at": None,
        }
    path = _USER_STRATEGIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="策略库不存在")
    return _read_json(path)


def create_personality_library(
    name: str,
    personalities: list[dict[str, Any]] | None = None,
    fork_from: str | None = None,
) -> dict[str, Any]:
    _ensure_user_dirs()
    if fork_from:
        source = get_personality_library(fork_from)
        base_personalities = [dict(p) for p in source["personalities"]]
    else:
        base_personalities = list(personalities or [])
    lib_id = str(uuid.uuid4())
    now = _now_iso()
    data = {
        "id": lib_id,
        "name": name.strip() or "未命名人格库",
        "is_builtin": False,
        "personalities": base_personalities,
        "created_at": now,
        "updated_at": now,
    }
    _write_json(_personality_path(lib_id), data)
    return data


def update_personality_library(
    library_id: str,
    *,
    name: str | None = None,
    personalities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    _reject_builtin_mutation(library_id, op="修改")
    path = _USER_PERSONALITIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="人格库不存在")
    data = _read_json(path)
    if name is not None:
        data["name"] = name.strip() or data["name"]
    if personalities is not None:
        data["personalities"] = personalities
    data["updated_at"] = _now_iso()
    _write_json(path, data)
    return data


def delete_personality_library(library_id: str) -> None:
    _reject_builtin_mutation(library_id, op="删除")
    path = _USER_PERSONALITIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="人格库不存在")
    path.unlink()


def create_strategy_library(
    name: str,
    strategies_by_role: dict[str, list[dict[str, Any]]] | None = None,
    fork_from: str | None = None,
) -> dict[str, Any]:
    _ensure_user_dirs()
    if fork_from:
        source = get_strategy_library(fork_from)
        base = {k: [dict(x) for x in v] for k, v in source["strategies_by_role"].items()}
    else:
        base = {k: [dict(x) for x in v] for k, v in (strategies_by_role or {}).items()}
    lib_id = str(uuid.uuid4())
    now = _now_iso()
    data = {
        "id": lib_id,
        "name": name.strip() or "未命名策略库",
        "is_builtin": False,
        "strategies_by_role": base,
        "created_at": now,
        "updated_at": now,
    }
    _write_json(_strategy_path(lib_id), data)
    return data


def update_strategy_library(
    library_id: str,
    *,
    name: str | None = None,
    strategies_by_role: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    _reject_builtin_mutation(library_id, op="修改")
    path = _USER_STRATEGIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="策略库不存在")
    data = _read_json(path)
    if name is not None:
        data["name"] = name.strip() or data["name"]
    if strategies_by_role is not None:
        data["strategies_by_role"] = strategies_by_role
    data["updated_at"] = _now_iso()
    _write_json(path, data)
    return data


def patch_strategy_library_extend(
    library_id: str,
    append_by_role: dict[str, list[dict[str, Any]]],
    name: str | None = None,
) -> dict[str, Any]:
    _reject_builtin_mutation(library_id, op="修改")
    path = _USER_STRATEGIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="策略库不存在")
    data = _read_json(path)
    if name is not None:
        data["name"] = name.strip() or data["name"]
    by_role: dict[str, list[dict[str, Any]]] = data.setdefault("strategies_by_role", {})
    for role_key, entries in append_by_role.items():
        if role_key not in _ROLE_VALUES:
            raise HTTPException(status_code=400, detail=f"无效身份: {role_key}")
        existing = by_role.setdefault(role_key, [])
        existing.extend(entries)
    data["updated_at"] = _now_iso()
    _write_json(path, data)
    return data


def delete_strategy_library(library_id: str) -> None:
    _reject_builtin_mutation(library_id, op="删除")
    path = _USER_STRATEGIES_DIR / f"{library_id}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="策略库不存在")
    path.unlink()


def resolve_personality_templates(library_id: str | None) -> list[dict[str, Any]]:
    lib_id = library_id or _BUILTIN_ID
    return list(get_personality_library(lib_id)["personalities"])


@lru_cache
def _cached_role_strategies(library_id: str, role_value: str) -> tuple[dict[str, Any], ...]:
    lib = get_strategy_library(library_id)
    items = lib.get("strategies_by_role", {}).get(role_value, [])
    return tuple(items)


def resolve_role_strategy_dicts(library_id: str | None, role: Role) -> list[dict[str, Any]]:
    lib_id = library_id or _BUILTIN_ID
    return list(_cached_role_strategies(lib_id, role.value))


def clear_strategy_cache() -> None:
    _cached_role_strategies.cache_clear()


def library_exists(library_id: str, *, kind: str) -> bool:
    if library_id == _BUILTIN_ID:
        return True
    if kind == "personality":
        return (_USER_PERSONALITIES_DIR / f"{library_id}.json").is_file()
    return (_USER_STRATEGIES_DIR / f"{library_id}.json").is_file()
