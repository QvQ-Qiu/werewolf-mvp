"""信念 / 逻辑链：结构化状态，仅合法信息"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.models.game import BeliefState, GameState, Role
from app.services.state_view import build_state_view_text

if TYPE_CHECKING:
    from app.llm.pipeline import LlmPipeline

logger = logging.getLogger(__name__)


def ensure_belief(state: GameState, seat: int) -> BeliefState:
    if seat not in state.belief_by_seat:
        state.belief_by_seat[seat] = BeliefState()
    return state.belief_by_seat[seat]


def update_belief_from_public_log(state: GameState, seat: int) -> None:
    """规则化更新信念（无 LLM 时的轻量逻辑链）"""
    belief = ensure_belief(state, seat)
    player = state.get_player(seat)

    for entry in state.public_log[-15:]:
        if entry.type == "speech" and entry.seat and entry.seat != seat:
            content = entry.content or ""
            if "预言家" in content or "我是预" in content:
                belief.role_claims[str(entry.seat)] = "seer_claim"
            if "狼" in content and entry.seat:
                if entry.seat not in belief.suspects:
                    belief.suspects.append(entry.seat)

    for vote in state.day_votes:
        if vote.voter_seat != seat and vote.target_seat:
            if vote.target_seat not in belief.suspects and vote.voter_seat in belief.suspects:
                belief.trusted.append(vote.voter_seat)

    if player.role == Role.SEER and seat == player.seat:
        for check in state.seer_checks:
            if check.is_wolf and check.target_seat not in belief.suspects:
                belief.suspects.append(check.target_seat)
            elif not check.is_wolf and check.target_seat not in belief.trusted:
                belief.trusted.append(check.target_seat)

    belief.suspects = list(dict.fromkeys(belief.suspects))[:6]
    belief.trusted = list(dict.fromkeys(belief.trusted))[:6]


def format_own_actions_for_belief(state: GameState, seat: int) -> str:
    """己方技能/策略/票型等私域记忆（不含重复公屏全文）。"""
    mem = state.player_memories.get(seat)
    if not mem:
        return "（无己方行动记录）"
    lines: list[str] = []
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
    return "\n".join(lines) if lines else "（无己方行动记录）"


def summarize_belief(state: GameState, seat: int) -> str:
    belief = state.belief_by_seat.get(seat) or BeliefState()
    parts = []
    if belief.suspects:
        parts.append(f"怀疑：{belief.suspects}")
    if belief.trusted:
        parts.append(f"信任：{belief.trusted}")
    if belief.role_claims:
        parts.append(f"身份声明：{belief.role_claims}")
    if belief.open_questions:
        parts.append(f"待验证：{belief.open_questions}")
    return "；".join(parts) if parts else "尚无明确结论，继续观察。"


def belief_to_json(belief: BeliefState) -> str:
    return json.dumps(belief.model_dump(), ensure_ascii=False)


def apply_belief_update_from_llm(state: GameState, seat: int, data: dict[str, Any]) -> None:
    belief = ensure_belief(state, seat)
    if "suspects" in data:
        belief.suspects = list(data["suspects"])[:8]
    if "trusted" in data:
        belief.trusted = list(data["trusted"])[:8]
    if "role_claims" in data:
        belief.role_claims = {str(k): v for k, v in data["role_claims"].items()}
    if "open_questions" in data:
        belief.open_questions = list(data["open_questions"])[:5]


async def update_belief_from_llm(
    state: GameState,
    seat: int,
    pipeline: LlmPipeline,
) -> bool:
    """投票前 LLM 信念更新；狼人跳过。返回是否成功应用 LLM 结果。"""
    player = state.get_player(seat)
    if player.role == Role.WOLF:
        return False

    update_belief_from_public_log(state, seat)

    if not settings.llm_belief_fast_mode:
        return False

    role = player.role or Role.VILLAGER
    try:
        data = await pipeline.run_belief_update_pipeline(state, seat, role)
    except Exception as exc:
        logger.warning("信念 LLM 更新失败 seat=%s: %s", seat, exc)
        return False

    apply_belief_update_from_llm(state, seat, data)
    return True


def build_belief_context_block(state: GameState, seat: int) -> str:
    update_belief_from_public_log(state, seat)
    view = build_state_view_text(state, seat)
    return f"{summarize_belief(state, seat)}\n合法视野摘要：{view[:800]}"
