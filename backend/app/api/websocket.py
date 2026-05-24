"""WebSocket 路由"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.game_loop import game_loop_registry
from app.services.game_registry import game_registry

router = APIRouter()


@router.websocket("/ws/games/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str, token: str = "") -> None:
    """对局 WebSocket：连接后由 GameLoop 驱动阶段推进"""
    await websocket.accept()

    state = game_registry.get(game_id)
    if state is None:
        await websocket.send_json(
            {"type": "ERROR", "payload": {"code": "NOT_FOUND", "message": "对局不存在"}}
        )
        await websocket.close()
        return

    if not token or not game_registry.verify_token(game_id, token):
        await websocket.send_json(
            {"type": "ERROR", "payload": {"code": "UNAUTHORIZED", "message": "无效 token"}}
        )
        await websocket.close()
        return

    human_seat = game_registry.human_seat(game_id)
    if human_seat is None:
        await websocket.send_json(
            {"type": "ERROR", "payload": {"code": "NO_HUMAN", "message": "对局无人类玩家"}}
        )
        await websocket.close()
        return

    human = state.get_player(human_seat)
    loop = game_loop_registry.get_or_create(
        game_id, state, human_seat, human.role  # type: ignore[arg-type]
    )

    await loop.add_connection(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await loop.connections.send_to(
                    websocket,
                    {"type": "ERROR", "payload": {"code": "INVALID_JSON", "message": "无效 JSON"}},
                )
                continue
            await loop.handle_client_event(websocket, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await loop.remove_connection(websocket)
