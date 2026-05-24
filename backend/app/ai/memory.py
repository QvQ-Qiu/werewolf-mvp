"""玩家记忆：策略史、公开承诺、投票/刀口历史"""

from __future__ import annotations

from datetime import datetime

from app.ai.memory_compress import format_public_memory_text
from app.models.game import (
    GameState,
    PlayerMemory,
    PublicClaim,
    StrategyUsageRecord,
)


def _phase_ref(state: GameState) -> str:
    sub = state.sub_phase.value if state.sub_phase else ""
    return f"day{state.day_number}_{state.phase.value}_{sub}"


def ensure_player_memory(state: GameState, seat: int) -> PlayerMemory:
    if seat not in state.player_memories:
        state.player_memories[seat] = PlayerMemory(seat=seat)
    return state.player_memories[seat]


def record_strategy_usage(
    state: GameState,
    seat: int,
    strategy_id: str,
    reason: str = "",
) -> None:
    mem = ensure_player_memory(state, seat)
    mem.strategy_history.append(
        StrategyUsageRecord(
            strategy_id=strategy_id,
            phase_ref=_phase_ref(state),
            reason=reason[:120],
        )
    )


def get_used_strategy_ids(state: GameState, seat: int) -> set[str]:
    mem = state.player_memories.get(seat)
    if not mem:
        return set()
    return {r.strategy_id for r in mem.strategy_history}


def record_public_claim(
    state: GameState,
    seat: int,
    claim_type: str,
    content: str,
    *,
    is_truthful: bool = True,
) -> None:
    mem = ensure_player_memory(state, seat)
    mem.public_claims.append(
        PublicClaim(
            day=state.day_number,
            claim_type=claim_type,
            content=content[:300],
            is_truthful=is_truthful,
        )
    )


def record_vote(state: GameState, voter_seat: int, target_seat: int | None) -> None:
    mem = ensure_player_memory(state, voter_seat)
    mem.vote_history.append(
        {
            "day": state.day_number,
            "target": target_seat,
            "phase_ref": _phase_ref(state),
        }
    )


def record_wolf_nomination(state: GameState, wolf_seat: int, target_seat: int) -> None:
    mem = ensure_player_memory(state, wolf_seat)
    mem.kill_history.append(
        {
            "night": state.day_number,
            "target": target_seat,
            "phase_ref": _phase_ref(state),
        }
    )


def record_seer_check_truth(
    state: GameState,
    seer_seat: int,
    target_seat: int,
    is_wolf: bool,
) -> None:
    """服务端记录真实验人结果（与公开报验分开）"""
    mem = ensure_player_memory(state, seer_seat)
    mem.seer_checks_truth.append(
        {
            "night": state.day_number,
            "target": target_seat,
            "is_wolf": is_wolf,
        }
    )


def format_memory_for_prompt(state: GameState, seat: int) -> str:
    mem = state.player_memories.get(seat)
    lines: list[str] = [format_public_memory_text(state)]
    if not mem:
        return lines[0] if lines[0] != "（暂无公开记录）" else "（暂无历史记录）"

    if mem.strategy_history:
        lines.append("【已用策略】")
        for r in mem.strategy_history[-8:]:
            lines.append(f"- [{r.phase_ref}] {r.strategy_id}: {r.reason or '无备注'}")

    if mem.public_claims:
        lines.append("【公开承诺/声明】")
        for c in mem.public_claims[-6:]:
            tag = "真" if c.is_truthful else "假/战术"
            lines.append(f"- [day{c.day}] ({tag}) {c.claim_type}: {c.content}")

    if mem.vote_history:
        lines.append("【投票历史】")
        for v in mem.vote_history[-6:]:
            t = v.get("target")
            lines.append(f"- day{v.get('day')}: 投 {t if t else '弃票'}")

    if mem.kill_history:
        lines.append("【刀口提名历史】")
        for k in mem.kill_history[-4:]:
            lines.append(f"- night{k.get('night')}: 提名 {k.get('target')}")

    if mem.seer_checks_truth:
        lines.append("【真实验人记录-仅自己可见】")
        for c in mem.seer_checks_truth[-5:]:
            result = "狼" if c.get("is_wolf") else "好人"
            lines.append(f"- night{c.get('night')}: {c.get('target')}号 → {result}")

    return "\n".join(lines) if lines else "（暂无历史记录）"


class PlayerMemoryStore:
    """兼容别名"""

    ensure = staticmethod(ensure_player_memory)
