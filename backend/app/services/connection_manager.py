"""WebSocket 连接管理：按对局广播事件"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import WebSocket


class ConnectionManager:
    """管理单个对局的所有 WebSocket 连接"""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, int | None] = {}  # ws -> 座位（None 为观战）
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, seat: int | None = None) -> None:
        async with self._lock:
            self._connections[websocket] = seat

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    @property
    def count(self) -> int:
        return len(self._connections)

    async def broadcast(self, event: dict[str, Any]) -> None:
        """向所有连接广播事件"""
        async with self._lock:
            targets = list(self._connections.keys())
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)

    async def send_to(self, websocket: WebSocket, event: dict[str, Any]) -> None:
        try:
            await websocket.send_json(event)
        except Exception:
            await self.disconnect(websocket)

    async def send_to_seat(self, seat: int, event: dict[str, Any]) -> None:
        """仅向指定座位的连接发送（私域消息）"""
        async with self._lock:
            targets = [ws for ws, s in self._connections.items() if s == seat]
        for ws in targets:
            await self.send_to(ws, event)

    async def broadcast_except_payload(
        self,
        base_event: dict[str, Any],
        payload_for_seat: Callable[[int | None], dict[str, Any]],
    ) -> None:
        """按座位定制 payload 后发送（视野过滤）"""
        async with self._lock:
            pairs = list(self._connections.items())
        dead: list[WebSocket] = []
        for ws, seat in pairs:
            event = {
                "type": base_event["type"],
                "payload": payload_for_seat(seat),
            }
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)
