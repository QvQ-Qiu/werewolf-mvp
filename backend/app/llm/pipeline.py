"""LLM 三步 Pipeline：选策略 → 行动 → 发言"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Awaitable, Callable
from typing import Any

from app.ai.belief import summarize_belief
from app.ai.memory import PlayerMemoryStore, record_strategy_usage
from app.ai.personality import get_personality_for_seat
from app.ai.strategy_library import StrategyEntry, select_strategy_weighted
from app.config import settings
from app.llm.client import LlmNotConfiguredError, QwenClient, get_qwen_client
from app.llm import prompts
from app.models.game import GameState, LlmTrace, Role
from app.services.state_view import build_state_view_text

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    strategy_id: str
    strategy_reason: str
    action: dict[str, Any] | None = None
    speech: str | None = None


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _prompt_hash(messages: list[dict[str, str]]) -> str:
    raw = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _phase_ref(state: GameState) -> str:
    sub = state.sub_phase.value if state.sub_phase else ""
    return f"day{state.day_number}_{state.phase.value}_{sub}"


def _append_trace(
    state: GameState,
    seat: int,
    step: str,
    messages: list[dict[str, str]],
    response: str,
    strategy_id: str | None = None,
) -> None:
    trace = LlmTrace(
        player_seat=seat,
        step=step,
        strategy_id=strategy_id,
        phase_ref=_phase_ref(state),
        prompt_summary=_prompt_hash(messages),
        response_summary=response[:2000],
        messages_full=list(messages),
        timestamp=datetime.utcnow(),
    )
    state.llm_traces.append(trace)
    logger.info(
        "llm_trace appended id=%s seat=%s step=%s phase=%s",
        trace.id,
        seat,
        step,
        trace.phase_ref,
    )


def clamp_speech(text: str, seat: int, personality: dict[str, Any]) -> str:
    max_chars = settings.llm_speech_max_chars
    if personality.get("low_logic"):
        max_chars = min(max_chars, 150)
    text = text.strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    if len(text) < settings.llm_speech_min_chars and len(text) < 20:
        text = f"{seat}号：{text}" if text else f"{seat}号：我先听听大家怎么说。"
    return text


class LlmPipeline:
    """三步 Pipeline 编排"""

    def __init__(self, client: QwenClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> QwenClient | None:
        if self._client is not None:
            return self._client
        return get_qwen_client()

    async def select_strategy(
        self,
        state: GameState,
        seat: int,
        role: Role,
        state_view: dict[str, Any],
        rng: Any,
    ) -> tuple[StrategyEntry, str]:
        personality = get_personality_for_seat(state, seat)
        personality_block = personality.get("_prompt_block", "")
        entry, reason = select_strategy_weighted(state, seat, role, personality, rng)

        client = self.client
        if client is None:
            return entry, reason

        from app.ai.strategy_library import get_candidates_for_role

        candidates = get_candidates_for_role(role, state.strategy_library_id)
        messages = prompts.build_strategy_select_messages(
            state, seat, role, state_view, candidates, personality_block
        )
        try:
            raw = await client.chat(messages, temperature=0.3, max_tokens=256)
            _append_trace(state, seat, "select_strategy", messages, raw)
            data = _parse_json_response(raw)
            sid = str(data.get("strategy_id", entry.id))
            matched = next((c for c in candidates if c.id == sid), None)
            if matched:
                entry = matched
            reason = str(data.get("reason", reason))
        except (LlmNotConfiguredError, json.JSONDecodeError, ValueError, Exception) as exc:
            logger.warning("策略选择 LLM 失败 seat=%s: %s，使用加权随机", seat, exc)

        record_strategy_usage(state, seat, entry.id, reason)
        return entry, reason

    async def decide_action(
        self,
        state: GameState,
        seat: int,
        role: Role,
        state_view: dict[str, Any],
        strategy: StrategyEntry,
        action_schema: str,
        *,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        extra_instructions: str = "",
    ) -> dict[str, Any]:
        personality = get_personality_for_seat(state, seat)
        personality_block = personality.get("_prompt_block", "")
        client = self.client
        if client is None:
            raise LlmNotConfiguredError("无 LLM 客户端")

        messages = prompts.build_action_decide_messages(
            state,
            seat,
            role,
            state_view,
            strategy,
            action_schema,
            personality_block,
            extra_instructions=extra_instructions,
        )
        raw = await client.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens if max_tokens is not None else 256,
        )
        _append_trace(state, seat, "decide_action", messages, raw, strategy.id)
        return _parse_json_response(raw)

    async def generate_speech(
        self,
        state: GameState,
        seat: int,
        role: Role,
        state_view: dict[str, Any],
        strategy: StrategyEntry,
    ) -> str:
        personality = get_personality_for_seat(state, seat)
        personality_block = personality.get("_prompt_block", "")
        belief_summary = summarize_belief(state, seat)
        client = self.client
        if client is None:
            raise LlmNotConfiguredError("无 LLM 客户端")

        messages = prompts.build_speech_messages(
            state,
            seat,
            role,
            state_view,
            strategy,
            belief_summary,
            personality_block,
            settings.llm_speech_min_chars,
            settings.llm_speech_max_chars,
        )
        raw = await client.chat(messages, temperature=0.8, max_tokens=512)
        _append_trace(state, seat, "generate_speech", messages, raw, strategy.id)
        return clamp_speech(raw, seat, personality)

    async def generate_speech_stream(
        self,
        state: GameState,
        seat: int,
        role: Role,
        state_view: dict[str, Any],
        strategy: StrategyEntry,
        on_delta: Callable[[str], Awaitable[None]],
    ) -> str:
        personality = get_personality_for_seat(state, seat)
        personality_block = personality.get("_prompt_block", "")
        belief_summary = summarize_belief(state, seat)
        client = self.client
        if client is None:
            raise LlmNotConfiguredError("无 LLM 客户端")

        messages = prompts.build_speech_messages(
            state,
            seat,
            role,
            state_view,
            strategy,
            belief_summary,
            personality_block,
            settings.llm_speech_min_chars,
            settings.llm_speech_max_chars,
        )
        parts: list[str] = []
        async for piece in client.chat_stream_messages(
            messages, temperature=0.8, max_tokens=512
        ):
            parts.append(piece)
            await on_delta(piece)
        raw = "".join(parts)
        _append_trace(state, seat, "generate_speech", messages, raw, strategy.id)
        return clamp_speech(raw, seat, personality)

    async def run_speech_pipeline(
        self,
        state: GameState,
        seat: int,
        role: Role,
        rng: Any,
    ) -> str:
        view = build_state_view_text(state, seat)
        strategy, _ = await self.select_strategy(state, seat, role, view, rng)
        return await self.generate_speech(state, seat, role, view, strategy)

    async def run_speech_pipeline_stream(
        self,
        state: GameState,
        seat: int,
        role: Role,
        rng: Any,
        on_delta: Callable[[str], Awaitable[None]],
    ) -> str:
        view = build_state_view_text(state, seat)
        strategy, _ = await self.select_strategy(state, seat, role, view, rng)
        return await self.generate_speech_stream(
            state, seat, role, view, strategy, on_delta
        )

    async def run_action_pipeline(
        self,
        state: GameState,
        seat: int,
        role: Role,
        action_schema: str,
        rng: Any,
    ) -> dict[str, Any]:
        view = build_state_view_text(state, seat)
        strategy, _ = await self.select_strategy(state, seat, role, view, rng)
        return await self.decide_action(state, seat, role, view, strategy, action_schema)

    async def run_night_action_pipeline(
        self,
        state: GameState,
        seat: int,
        role: Role,
        action_schema: str,
        rng: Any,
    ) -> dict[str, Any]:
        """夜晚行动：本地选策略 + 一次 LLM 决策（省掉 select_strategy 的 LLM 调用）。"""
        view = build_state_view_text(state, seat)
        personality = get_personality_for_seat(state, seat)
        entry, reason = select_strategy_weighted(state, seat, role, personality, rng)
        record_strategy_usage(state, seat, entry.id, reason)
        return await self.decide_action(
            state,
            seat,
            role,
            view,
            entry,
            action_schema,
            max_tokens=settings.llm_night_max_tokens,
        )

    async def run_wolf_nominate_pipeline(
        self,
        state: GameState,
        seat: int,
        action_schema: str,
        candidates: list[int],
        rng: Any,
    ) -> dict[str, Any]:
        """狼刀提名：座位独立 RNG + 更高温度 + 独立决策提示，避免多狼输出趋同。"""
        view = build_state_view_text(state, seat)
        personality = get_personality_for_seat(state, seat)
        seat_rng = random.Random(
            hash((state.seed, seat, state.day_number, 7919)) & 0xFFFFFFFF
        )
        entry, reason = select_strategy_weighted(state, seat, Role.WOLF, personality, seat_rng)
        record_strategy_usage(state, seat, entry.id, reason)
        extra = prompts.build_wolf_nominate_extra(seat, candidates, personality)
        return await self.decide_action(
            state,
            seat,
            Role.WOLF,
            view,
            entry,
            action_schema,
            max_tokens=settings.llm_night_max_tokens,
            temperature=0.65,
            extra_instructions=extra,
        )

    async def run_vote_action_pipeline(
        self,
        state: GameState,
        seat: int,
        role: Role,
        action_schema: str,
        rng: Any,
    ) -> dict[str, Any]:
        """白天投票：本地选策略 + 一次 LLM 决策（与夜晚 pipeline 独立）。"""
        view = build_state_view_text(state, seat)
        personality = get_personality_for_seat(state, seat)
        entry, reason = select_strategy_weighted(state, seat, role, personality, rng)
        record_strategy_usage(state, seat, entry.id, reason)
        return await self.decide_action(
            state,
            seat,
            role,
            view,
            entry,
            action_schema,
            max_tokens=settings.llm_vote_max_tokens,
        )

def get_pipeline() -> LlmPipeline:
    return LlmPipeline()
