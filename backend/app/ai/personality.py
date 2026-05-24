"""人格系统：每局为 9 个 AI 随机分配不重复人格"""

from __future__ import annotations

import random
from typing import Any

from app.models.game import GameState, Player
from app.services.library_store import resolve_personality_templates

_MAX_LOW_LOGIC = 3


def load_personality_templates(library_id: str | None = None) -> list[dict[str, Any]]:
    return resolve_personality_templates(library_id)


def format_personality_block(persona: dict[str, Any]) -> str:
    return (
        f"人格：{persona.get('name', persona.get('id'))}\n"
        f"攻击性 {persona.get('aggression', 0.5):.1f}，逻辑性 {persona.get('logic', 0.5):.1f}\n"
        f"文风：{persona.get('style_hint', '')}\n"
        f"决策倾向：{persona.get('decision_bias', '')}"
    )


def assign_personalities_to_ai(state: GameState, rng: random.Random) -> None:
    """为所有 AI 玩家分配不重复人格，写入 state.personality_by_seat 与 player.persona_id"""
    templates = load_personality_templates(state.personality_library_id)
    ai_seats = [p.seat for p in state.players if not p.is_human]
    if len(ai_seats) > len(templates):
        raise ValueError("人格模板数量不足")

    chosen = rng.sample(templates, len(ai_seats))
    low_logic_assigned = 0

    state.personality_by_seat = {}
    for seat, persona in zip(sorted(ai_seats), chosen, strict=True):
        persona = dict(persona)
        if persona.get("low_logic") and low_logic_assigned >= _MAX_LOW_LOGIC:
            persona["low_logic"] = False
        if persona.get("low_logic"):
            low_logic_assigned += 1
        persona["_prompt_block"] = format_personality_block(persona)
        state.personality_by_seat[seat] = persona
        player = state.get_player(seat)
        player.persona_id = persona["id"]


def get_personality_for_seat(state: GameState, seat: int) -> dict[str, Any]:
    if seat in state.personality_by_seat:
        return state.personality_by_seat[seat]
    return {
        "id": "default",
        "name": "默认",
        "aggression": 0.5,
        "logic": 0.5,
        "style_hint": "中性发言",
        "decision_bias": "neutral",
        "low_logic": False,
        "_prompt_block": "人格：默认中性",
    }


def get_personality_for_player(state: GameState, player: Player) -> dict[str, Any]:
    return get_personality_for_seat(state, player.seat)
