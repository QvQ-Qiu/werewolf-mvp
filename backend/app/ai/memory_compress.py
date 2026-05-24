"""公共记忆按天压缩：夜晚异步摘要，天亮前合并进 working memory"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.config import settings
from app.models.game import PublicLogEntry

if TYPE_CHECKING:
    from app.models.game import GameState

logger = logging.getLogger(__name__)


def _format_log_line(entry: PublicLogEntry) -> str:
    seat = f"{entry.seat}号" if entry.seat is not None else ""
    if entry.type == "speech" and entry.seat is not None:
        return f"[发言] {seat}：{entry.content[:120]}"
    if entry.type == "death":
        return f"[死亡] {entry.content}"
    if entry.type == "vote":
        return f"[投票] {entry.content[:160]}"
    return f"[{entry.type}] {entry.content[:160]}"


def summarize_public_log_rule_based(
    entries: list[PublicLogEntry],
    *,
    day_number: int,
) -> str:
    """规则摘要（无 LLM 时的 fallback）"""
    if not entries:
        return f"第{day_number}天：无公开事件。"

    speeches = sum(1 for e in entries if e.type == "speech")
    deaths = [e for e in entries if e.type == "death"]
    votes = [e for e in entries if e.type == "vote"]
    systems = [e.content for e in entries if e.type == "system"]

    parts = [f"第{day_number}天摘要："]
    if systems:
        parts.append("；".join(systems[:4]))
    if speeches:
        parts.append(f"共{speeches}条发言。")
        for e in entries:
            if e.type == "speech" and e.seat is not None:
                parts.append(f"{e.seat}号：{e.content[:60]}…")
                break
    if deaths:
        parts.append("死亡：" + "；".join(d.content for d in deaths[:3]))
    if votes:
        parts.append("投票：" + votes[-1].content[:100])
    return " ".join(parts)[:600]


async def summarize_public_log_llm(
    entries: list[PublicLogEntry],
    *,
    day_number: int,
) -> str:
    """LLM 压缩摘要；失败时回退规则摘要"""
    if not entries:
        return summarize_public_log_rule_based(entries, day_number=day_number)

    lines = "\n".join(_format_log_line(e) for e in entries[-40:])
    prompt = f"""请将以下狼人杀第{day_number}天公屏记录压缩为 2～4 句中文摘要，保留关键死亡、投票、跳身份与重要发言要点。不要编造未出现的信息。

{lines}

只输出摘要正文。"""

    try:
        from app.ai.orchestrator import is_llm_enabled
        from app.llm.client import LlmNotConfiguredError, get_qwen_client

        if not is_llm_enabled():
            return summarize_public_log_rule_based(entries, day_number=day_number)

        client = get_qwen_client()
        text = await client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=settings.llm_memory_compress_max_tokens,
        )
        cleaned = (text or "").strip()
        if cleaned:
            return cleaned[:800]
    except (LlmNotConfiguredError, Exception) as exc:
        logger.debug("memory compress LLM fallback: %s", exc)

    return summarize_public_log_rule_based(entries, day_number=day_number)


async def compress_round_entries(
    entries: list[PublicLogEntry],
    *,
    day_number: int,
) -> str:
    return await summarize_public_log_llm(entries, day_number=day_number)


def get_current_round_public_log(state: GameState) -> list[PublicLogEntry]:
    """当前天（进行中）完整公屏片段"""
    start = max(0, state.current_round_log_start_index)
    return state.public_log[start:]


def format_public_memory_for_view(state: GameState) -> dict[str, object]:
    """供 state_view / prompt 注入的公共记忆结构"""
    current = get_current_round_public_log(state)
    return {
        "round_summaries": list(state.round_memory_summaries),
        "current_round_log": [
            {
                "seat": e.seat,
                "content": e.content,
                "type": e.type,
            }
            for e in current
        ],
    }


def format_public_memory_text(state: GameState) -> str:
    """将压缩摘要 + 当前天完整日志格式化为 prompt 文本块"""
    mem = format_public_memory_for_view(state)
    lines: list[str] = []
    summaries: list[str] = mem["round_summaries"]  # type: ignore[assignment]
    if summaries:
        lines.append("【历史天摘要】")
        for i, s in enumerate(summaries, start=1):
            lines.append(f"- 第{i}天：{s}")
    current: list[dict] = mem["current_round_log"]  # type: ignore[assignment]
    if current:
        lines.append("【当前天公屏】")
        for e in current[-30:]:
            seat = e.get("seat")
            prefix = f"{seat}号" if seat else ""
            if e.get("type") == "speech":
                lines.append(f"- {prefix}：{e.get('content', '')}")
            else:
                lines.append(f"- [{e.get('type')}] {e.get('content', '')}")
    return "\n".join(lines) if lines else "（暂无公开记录）"


async def run_compression_task(
    state: GameState,
    from_index: int,
    day_number: int,
) -> str:
    """压缩 [from_index, len(public_log)) 区间并返回摘要"""
    entries = state.public_log[from_index:]
    return await compress_round_entries(entries, day_number=day_number)


def apply_round_compression(state: GameState, summary: str) -> None:
    """天亮前将上一日摘要写入 round_memory_summaries，并切换当前天起点"""
    if summary.strip():
        state.round_memory_summaries.append(summary.strip())
    state.current_round_log_start_index = len(state.public_log)
