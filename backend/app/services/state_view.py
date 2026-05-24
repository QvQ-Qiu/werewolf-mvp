"""视野过滤：存活玩家仅见合法信息 + 自己私域"""

from __future__ import annotations

import json
from typing import Any

from app.ai.memory_compress import format_public_memory_for_view, get_current_round_public_log
from app.ai.private_channel import private_messages_for_seat
from app.models.game import GameState, Phase, Role, SubPhase


def build_speech_phase_context(game: GameState) -> dict[str, Any] | None:
    """白天发言阶段的顺序与进度（供 LLM 理解「已过麦不可再发言」）。"""
    if game.sub_phase != SubPhase.DAY_SPEECH or not game.speech_order:
        return None

    order = list(game.speech_order)
    idx = game.current_speaker_index
    already_spoken = order[:idx]
    current = order[idx] if idx < len(order) else None
    pending = order[idx + 1 :] if current is not None else []

    status_by_seat: dict[int, str] = {}
    for i, seat in enumerate(order):
        if i < idx:
            status_by_seat[seat] = "done"
        elif i == idx:
            status_by_seat[seat] = "current"
        else:
            status_by_seat[seat] = "pending"

    parts: list[str] = [f"发言顺序：{'→'.join(str(s) for s in order)}"]
    if already_spoken:
        parts.append(f"已发言/过麦（本轮不可再开口）：{','.join(str(s) for s in already_spoken)}")
    if current is not None:
        parts.append(f"当前轮到：{current}号")
    if pending:
        parts.append(f"尚未发言：{','.join(str(s) for s in pending)}")

    return {
        "speech_order": order,
        "current_speaker_index": idx,
        "already_spoken_seats": already_spoken,
        "current_speaker_seat": current,
        "pending_speaker_seats": pending,
        "speech_status_by_seat": status_by_seat,
        "summary": "。".join(parts),
    }


def build_public_view(game: GameState, player_id: int) -> dict[str, Any]:
    """
    为指定座位构建合法视野（用于 LLM 与 WebSocket 过滤）。
    不含他人身份、他人验人。
    """
    player = game.get_player(player_id)
    alive = player.is_alive

    current_round = get_current_round_public_log(game)
    speeches = [
        {"seat": e.seat, "content": e.content, "type": e.type}
        for e in current_round
        if e.type in ("speech", "system", "vote", "death", "skill_reveal")
    ]
    public_memory = format_public_memory_for_view(game)

    view: dict[str, Any] = {
        "your_seat": player_id,
        "your_role": player.role.value if player.role else None,
        "phase": game.phase.value,
        "sub_phase": game.sub_phase.value if game.sub_phase else None,
        "day_number": game.day_number,
        "alive_seats": sorted(game.alive_seats),
        "public_log": speeches[-30:],
        "public_memory": public_memory,
        "day_votes": [
            {"voter": v.voter_seat, "target": v.target_seat}
            for v in game.day_votes
        ],
        "last_night_deaths": game.last_night_deaths,
        "last_exiled_seat": game.last_exiled_seat,
        "you_are_alive": alive,
    }

    # 自己的验人结果
    if player.role == Role.SEER:
        view["your_seer_checks"] = [
            {"night": c.night, "target": c.target_seat, "is_wolf": c.is_wolf}
            for c in game.seer_checks
        ]

    # 女巫：药状态 + 当夜刀口（进入女巫阶段后由状态机推算）
    if player.role == Role.WITCH:
        view["witch_heal_available"] = game.witch_state.heal_available
        view["witch_poison_available"] = game.witch_state.poison_available
        if game.sub_phase in (
            SubPhase.NIGHT_WITCH,
            SubPhase.NIGHT_GUARD,
            SubPhase.NIGHT_RESOLVE,
        ) and game.wolf_kill_target is not None:
            view["wolf_kill_target"] = game.wolf_kill_target

    # 狼人可见队友座位（不含具体刀口协商细节以外的队友身份已自知）
    if player.role == Role.WOLF and alive:
        view["wolf_teammates"] = [
            p.seat for p in game.players if p.role == Role.WOLF and p.seat != player_id
        ]

    # 私域：仅自己的
    priv = private_messages_for_seat(game, player_id)
    view["private_messages"] = [
        {
            "channel": m.channel,
            "sender": m.sender_seat,
            "content": m.content,
            "phase_ref": m.phase_ref,
        }
        for m in priv[-10:]
    ]

    if not alive:
        view["spectator_mode"] = True
        view["note"] = "你已出局，可观战；完整 AI 链复盘见 Phase 4"

    speech_ctx = build_speech_phase_context(game)
    if speech_ctx is not None:
        speech_ctx = dict(speech_ctx)
        speech_ctx["is_your_turn"] = speech_ctx.get("current_speaker_seat") == player_id
        view["speech_phase"] = speech_ctx

    return view


def build_state_view_text(game: GameState, player_id: int) -> dict[str, Any]:
    """Pipeline 用的 JSON 友好视图"""
    return build_public_view(game, player_id)


def filter_snapshot_for_player(snapshot: dict[str, Any], game: GameState, seat: int) -> dict[str, Any]:
    """过滤 STATE_SNAPSHOT，移除越权字段"""
    view = build_public_view(game, seat)
    out = dict(snapshot)
    out["filtered_view"] = view
    if not game.get_player(seat).is_alive:
        out["spectator_mode"] = True
    return out
