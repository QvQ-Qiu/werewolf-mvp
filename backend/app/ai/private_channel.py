"""私域频道：预言家验人结果等（不进公屏）"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Awaitable

from app.models.game import GameState, PrivateMessage


def _phase_ref(state: GameState) -> str:
    sub = state.sub_phase.value if state.sub_phase else ""
    return f"day{state.day_number}_{state.phase.value}_{sub}"


def append_private_message(
    state: GameState,
    *,
    receiver_seat: int,
    content: str,
    channel: str,
    sender_seat: int | None = None,
    visible_to: list[int] | None = None,
) -> PrivateMessage:
    msg = PrivateMessage(
        id=str(uuid.uuid4())[:8],
        sender_seat=sender_seat,
        receiver_seat=receiver_seat,
        channel=channel,
        content=content,
        phase_ref=_phase_ref(state),
        visible_to=visible_to or [receiver_seat],
        timestamp=datetime.utcnow(),
    )
    state.private_messages.append(msg)
    return msg


async def broadcast_private_event(
    send_fn: Callable[[int, dict[str, Any]], Awaitable[None]],
    seat: int,
    msg: PrivateMessage,
) -> None:
    """通过 WebSocket 发送 PRIVATE_MESSAGE"""
    await send_fn(
        seat,
        {
            "type": "PRIVATE_MESSAGE",
            "payload": {
                "id": msg.id,
                "channel": msg.channel,
                "sender_seat": msg.sender_seat,
                "receiver_seat": msg.receiver_seat,
                "content": msg.content,
                "phase_ref": msg.phase_ref,
                "timestamp": msg.timestamp.isoformat(),
            },
        },
    )


async def send_seer_result(
    state: GameState,
    seer_seat: int,
    target_seat: int,
    is_wolf: bool,
    send_fn: Callable[[int, dict[str, Any]], Awaitable[None]] | None,
) -> PrivateMessage:
    result = "狼人" if is_wolf else "好人"
    content = f"【验人结果】{target_seat} 号是{result}"
    msg = append_private_message(
        state,
        receiver_seat=seer_seat,
        sender_seat=None,
        content=content,
        channel="seer_result",
        visible_to=[seer_seat],
    )
    if send_fn:
        await broadcast_private_event(send_fn, seer_seat, msg)
    return msg


def private_messages_for_seat(state: GameState, seat: int) -> list[PrivateMessage]:
    return [m for m in state.private_messages if seat in m.visible_to]
