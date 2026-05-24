"""REST API 路由"""

import uuid

from fastapi import APIRouter, HTTPException

from app.models.actions import Action, ActionType
from app.models.game import (
    AdvancePhaseResponse,
    CreateGameRequest,
    CreateGameResponse,
    GameListItem,
    GameReplayResponse,
    GameSummary,
    PlayerPublicInfo,
    SubmitActionRequest,
    SubmitActionResponse,
)
from app.services import library_store, replay_store
from app.services.game_registry import game_registry
from app.services.replay_view import build_game_replay

router = APIRouter()


def _resolve_state(game_id: str):
    state = game_registry.get(game_id)
    if state is not None:
        return state, True
    loaded = replay_store.load_state(game_id)
    if loaded is not None:
        return loaded, False
    return None, False


def _verify_replay_access(game_id: str, token: str, from_memory: bool) -> None:
    if not token:
        return
    if from_memory:
        if not game_registry.verify_token(game_id, token):
            raise HTTPException(status_code=403, detail="无效 token")
    elif not replay_store.verify_token(game_id, token):
        raise HTTPException(status_code=403, detail="无效 token")


@router.get("/health")
async def health_check() -> dict:
    from app.llm.health import llm_status

    return {"status": "ok", "llm": llm_status()}


@router.get("/games", response_model=list[GameListItem])
async def list_games(in_progress_only: bool = False) -> list[GameListItem]:
    """列出内存中的活跃/历史对局"""
    return game_registry.list_games(in_progress_only=in_progress_only)


@router.post("/games", response_model=CreateGameResponse)
async def create_game(body: CreateGameRequest) -> CreateGameResponse:
    personality_lib = body.personality_library_id or "default"
    strategy_lib = body.strategy_library_id or "default"
    if not library_store.library_exists(personality_lib, kind="personality"):
        raise HTTPException(status_code=400, detail=f"人格库不存在: {personality_lib}")
    if not library_store.library_exists(strategy_lib, kind="strategy"):
        raise HTTPException(status_code=400, detail=f"策略库不存在: {strategy_lib}")

    game_id = str(uuid.uuid4())
    player_token = str(uuid.uuid4())
    state, human_seat = game_registry.create(
        game_id,
        player_name=body.player_name,
        player_token=player_token,
        seed=body.seed,
        personality_library_id=personality_lib,
        strategy_library_id=strategy_lib,
    )
    human = state.get_player(human_seat)
    return CreateGameResponse(
        game_id=game_id,
        ws_url=f"/ws/games/{game_id}?token={player_token}",
        player_token=player_token,
        human_seat=human_seat,
        human_role=human.role,  # type: ignore[arg-type]
    )


@router.get("/games/{game_id}", response_model=GameSummary)
async def get_game(game_id: str) -> GameSummary:
    game, _ = _resolve_state(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    return GameSummary(
        game_id=game.game_id,
        status=game.status,
        phase=game.phase,
        sub_phase=game.sub_phase,
        day_number=game.day_number,
        winner=game.winner,
        players=[
            PlayerPublicInfo(
                seat=p.seat,
                name=p.name,
                is_alive=p.is_alive,
                is_human=p.is_human,
            )
            for p in game.players
        ],
        public_log=game.public_log,
    )


@router.get("/games/{game_id}/replay", response_model=GameReplayResponse)
async def get_game_replay(game_id: str, token: str = "") -> GameReplayResponse:
    game, from_memory = _resolve_state(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    _verify_replay_access(game_id, token, from_memory)
    human_seat = game_registry.human_seat(game_id)
    if human_seat is None:
        record = replay_store.load_record(game_id)
        human_seat = int(record["human_seat"]) if record else 1
    return build_game_replay(game, human_seat)


@router.get("/games/{game_id}/traces/{seat}")
async def get_seat_traces(game_id: str, seat: int, token: str = "") -> dict:
    """单座位完整 LLM 追溯（含 messages_full）"""
    game, from_memory = _resolve_state(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    _verify_replay_access(game_id, token, from_memory)
    traces = [t for t in game.llm_traces if t.player_seat == seat]
    return {
        "game_id": game_id,
        "seat": seat,
        "traces": [t.model_dump(mode="json") for t in traces],
    }


@router.post("/games/{game_id}/actions", response_model=SubmitActionResponse)
async def submit_action(game_id: str, body: SubmitActionRequest) -> SubmitActionResponse:
    engine = game_registry.get_engine(game_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    try:
        action_type = ActionType(body.action_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无效行动类型: {body.action_type}") from exc

    action = Action(
        action_type=action_type,
        actor_seat=body.actor_seat,
        target_seat=body.target_seat,
        content=body.content,
    )
    result = engine.apply_action(action)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.message)

    if result.sub_phase_complete:
        engine.advance_phase()

    state = engine.state
    return SubmitActionResponse(
        ok=True,
        message=result.message,
        sub_phase_complete=result.sub_phase_complete,
        phase=state.phase,
        sub_phase=state.sub_phase,
        winner=state.winner,
    )


@router.post("/games/{game_id}/advance", response_model=AdvancePhaseResponse)
async def advance_phase(game_id: str) -> AdvancePhaseResponse:
    engine = game_registry.get_engine(game_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    if not engine.is_sub_phase_complete() and not engine._should_auto_skip_sub_phase():
        raise HTTPException(status_code=400, detail="当前子阶段行动未收集完成")
    msg = engine.advance_phase()
    state = engine.state
    return AdvancePhaseResponse(
        ok=True,
        message=msg,
        phase=state.phase,
        sub_phase=state.sub_phase,
        winner=state.winner,
    )
