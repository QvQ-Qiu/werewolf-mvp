"""复盘视图：从 GameState 组装局后披露数据"""

from __future__ import annotations

from app.ai.personality import get_personality_for_seat
from app.models.game import (
    BeliefStateDto,
    GameReplayResponse,
    GameState,
    PlayerMemoryDto,
    ReplayPlayerInfo,
    Role,
)


def build_game_replay(state: GameState, human_seat: int) -> GameReplayResponse:
    players: list[ReplayPlayerInfo] = []
    for p in state.players:
        persona = get_personality_for_seat(state, p.seat) if not p.is_human else {}
        players.append(
            ReplayPlayerInfo(
                seat=p.seat,
                name=p.name,
                role=p.role or Role.VILLAGER,
                is_alive=p.is_alive,
                is_human=p.is_human,
                persona_id=p.persona_id,
                personality_name=persona.get("name") if persona else None,
            )
        )

    beliefs = [
        BeliefStateDto(
            seat=seat,
            suspects=list(b.suspects),
            trusted=list(b.trusted),
            role_claims=dict(b.role_claims),
            open_questions=list(b.open_questions),
        )
        for seat, b in sorted(state.belief_by_seat.items())
    ]

    memories = [
        PlayerMemoryDto(
            seat=mem.seat,
            strategy_history=[s.model_dump() for s in mem.strategy_history],
            public_claims=[c.model_dump() for c in mem.public_claims],
            vote_history=list(mem.vote_history),
        )
        for mem in state.player_memories.values()
    ]

    return GameReplayResponse(
        game_id=state.game_id,
        status=state.status,
        phase=state.phase,
        day_number=state.day_number,
        winner=state.winner,
        human_seat=human_seat,
        players=players,
        public_log=list(state.public_log),
        llm_traces=list(state.llm_traces),
        private_messages=list(state.private_messages),
        belief_by_seat=beliefs,
        player_memories=memories,
    )
