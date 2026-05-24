"""策略库：按身份加载，倾向性加权选择"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from app.ai.memory import get_used_strategy_ids
from app.models.game import GameState, Role
from app.services.library_store import resolve_role_strategy_dicts

_ROLE_FILES = {
    Role.WOLF: "wolf.json",
    Role.SEER: "seer.json",
    Role.WITCH: "witch.json",
    Role.HUNTER: "hunter.json",
    Role.GUARD: "guard.json",
    Role.VILLAGER: "villager.json",
}


@dataclass
class StrategyEntry:
    id: str
    role: str
    name: str
    tendency: str
    priority: int
    weight: float
    prompt_hint: str

    def effective_weight(self, personality: dict[str, Any]) -> float:
        w = self.weight
        bias = personality.get("decision_bias", "")
        if bias == "push_vote" and self.tendency in ("aggressive", "leader"):
            w *= 1.2
        if bias == "follow_majority" and self.tendency in ("passive", "follow", "low_profile"):
            w *= 1.25
        if bias == "fake_claim" and self.tendency == "fake_seer":
            w *= 1.3
        if personality.get("low_logic"):
            w *= 0.9
        return w * (1 + self.priority * 0.05)


def _parse_entry(raw: dict[str, Any]) -> StrategyEntry:
    return StrategyEntry(
        id=raw["id"],
        role=raw["role"],
        name=raw["name"],
        tendency=raw.get("tendency", ""),
        priority=int(raw.get("priority", 3)),
        weight=float(raw.get("weight", 1.0)),
        prompt_hint=raw.get("prompt_hint", ""),
    )


def get_candidates_for_role(role: Role, library_id: str | None = None) -> list[StrategyEntry]:
    items = resolve_role_strategy_dicts(library_id, role)
    return [_parse_entry(x) for x in items]


def select_strategy_weighted(
    state: GameState,
    seat: int,
    role: Role,
    personality: dict[str, Any],
    rng: random.Random,
) -> tuple[StrategyEntry, str]:
    """按权重随机选策略（无 LLM 时的兜底）"""
    candidates = get_candidates_for_role(role, state.strategy_library_id)
    if not candidates:
        fallback = StrategyEntry("X00", role.value, "默认", "default", 1, 1.0, "按局势行动")
        return fallback, "无策略库条目，使用默认"

    used = get_used_strategy_ids(state, seat)
    pool = [c for c in candidates if c.id not in used] or candidates
    weights = [c.effective_weight(personality) for c in pool]
    chosen = rng.choices(pool, weights=weights, k=1)[0]
    return chosen, f"加权选择 {chosen.name}"
