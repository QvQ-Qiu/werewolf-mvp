"""WebSocket 事件模型"""

from typing import Any, Optional

from pydantic import BaseModel


class WsEvent(BaseModel):
    """WebSocket 事件基类"""

    type: str
    payload: dict[str, Any] = {}


class PhaseChangedPayload(BaseModel):
    phase: str
    day_number: int
    sub_phase: Optional[str] = None


class PublicLogPayload(BaseModel):
    entry: dict[str, Any]


class SpeakTurnPayload(BaseModel):
    seat: int
    deadline_ts: float
    is_you: bool


class VoteStartedPayload(BaseModel):
    candidates: list[int]


class VoteResultPayload(BaseModel):
    tally: dict[int, int]
    eliminated_seat: Optional[int] = None
    is_tie: bool = False


class NightActionRequestPayload(BaseModel):
    action_type: str
    actor_seat: int
    alive_seats: list[int]


class GameStartedPayload(BaseModel):
    your_role: str
    your_seat: int
    players: list[dict[str, Any]]
