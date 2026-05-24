"""对局主循环：阶段推进、发言调度、Mock AI、WebSocket 广播"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import WebSocket

from app.config import settings
from app.game.engine import ApplyResult, RuleEngine, create_engine
from app.models.actions import Action, ActionType
from app.models.game import Faction, GameState, GameStatus, Phase, Role, SubPhase
from app.ai.memory import record_seer_check_truth
from app.ai.memory_compress import apply_round_compression, run_compression_task
from app.ai.orchestrator import is_llm_enabled, submit_night_for_ai, submit_speech, submit_vote
from app.game.roles import resolve_seer_check, seer_check_is_wolf
from app.services.auto_player import auto_submit_human_night, needs_human_night_action
from app.services.state_view import build_public_view, filter_snapshot_for_player
from app.services.connection_manager import ConnectionManager
from app.services.game_registry import game_registry
from app.services import replay_store


class GameLoop:
    """单局阶段调度器"""

    def __init__(
        self,
        game_id: str,
        state: GameState,
        human_seat: int,
        human_role: Role,
    ) -> None:
        self.game_id = game_id
        self.state = state
        self.human_seat = human_seat
        self.human_role = human_role
        self.connections = ConnectionManager()
        self._engine = create_engine(state)
        self._task: asyncio.Task | None = None
        self._last_log_index = 0
        self._last_phase_key: tuple[Any, ...] | None = None
        self._pending_speech: asyncio.Future[str | None] | None = None
        self._pending_vote: asyncio.Future[int | None] | None = None
        self._pending_night: asyncio.Future[dict[str, Any] | None] | None = None
        self._current_speech_seat: int | None = None
        self._vote_started = False
        self._vote_ai_batch_done = False
        self._last_trace_index = 0
        self._spectator_sent = False
        self._game_started_at = time.time()
        self._game_over_broadcast = False
        self._timeout_handled = False
        self._wolf_kill_result_sent_for_night: int | None = None
        self._memory_compress_task: asyncio.Task[str] | None = None
        self._memory_compress_from_index: int = 0
        self._memory_compress_day: int = 0
        self._pending_seer_ack: asyncio.Future[None] | None = None

    _SUB_PHASE_ACTIVE_ROLE: dict[SubPhase, Role] = {
        SubPhase.NIGHT_WOLF: Role.WOLF,
        SubPhase.NIGHT_SEER: Role.SEER,
        SubPhase.NIGHT_WITCH: Role.WITCH,
        SubPhase.NIGHT_GUARD: Role.GUARD,
    }

    async def _send_action_ack(
        self,
        seat: int,
        kind: str,
        message: str,
        *,
        success: bool = True,
    ) -> None:
        await self.connections.send_to_seat(
            seat,
            {
                "type": "ACTION_ACK",
                "payload": {
                    "kind": kind,
                    "message": message,
                    "success": success,
                    "seat": seat,
                },
            },
        )

    @property
    def engine(self) -> RuleEngine:
        return self._engine

    def _speech_seconds(self) -> int:
        return settings.game_speech_max_seconds

    async def add_connection(self, websocket: WebSocket) -> None:
        await self.connections.connect(websocket, self.human_seat)
        await self._send_initial_events(websocket)
        await self.ensure_running()

    async def remove_connection(self, websocket: WebSocket) -> None:
        await self.connections.disconnect(websocket)
        if self.connections.count == 0 and self._task and not self._task.done():
            self._task.cancel()

    async def ensure_running(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def handle_client_event(self, websocket: WebSocket, msg: dict[str, Any]) -> None:
        event_type = msg.get("type", "")
        payload = msg.get("payload") or {}

        if event_type == "PING":
            await self.connections.send_to(websocket, {"type": "PONG", "payload": {}})
            return

        if event_type == "SUBMIT_SPEECH":
            content = str(payload.get("content", "")).strip()
            if self._pending_speech and not self._pending_speech.done():
                if self._current_speech_seat == self.human_seat:
                    self._pending_speech.set_result(content or "")
                else:
                    await self._send_error(websocket, "NOT_YOUR_TURN", "当前不是你的发言回合")
            else:
                await self._send_error(websocket, "NOT_SPEECH_PHASE", "当前不是发言阶段")
            return

        if event_type == "SKIP_SPEECH":
            if self._pending_speech and not self._pending_speech.done():
                if self._current_speech_seat == self.human_seat:
                    self._pending_speech.set_result("")
                else:
                    await self._send_error(websocket, "NOT_YOUR_TURN", "当前不是你的发言回合")
            else:
                await self._send_error(websocket, "NOT_SPEECH_PHASE", "当前不是发言阶段")
            return

        if event_type == "SUBMIT_VOTE":
            if self.state.sub_phase != SubPhase.DAY_VOTE:
                await self._send_error(websocket, "NOT_VOTE_PHASE", "当前不是投票阶段")
                return
            human = self.state.get_player(self.human_seat)
            if not human.is_alive:
                await self._send_error(websocket, "NOT_ALIVE", "你已出局，无法投票")
                return
            if any(v.voter_seat == self.human_seat for v in self.state.day_votes):
                await self._send_error(websocket, "ALREADY_VOTED", "你已经投过票了")
                return
            target = payload.get("target_seat")
            if target is not None:
                target = int(target)
            result = self._engine.apply_action(
                Action(
                    action_type=ActionType.VOTE,
                    actor_seat=self.human_seat,
                    target_seat=target,
                )
            )
            vote_msg = "已弃票" if target is None else f"已投票给 {target} 号"
            await self._send_action_ack(
                self.human_seat,
                "vote",
                result.message or vote_msg,
                success=result.ok,
            )
            if self._pending_vote is not None and not self._pending_vote.done():
                self._pending_vote.set_result(target)
            return

        if event_type == "SUBMIT_NIGHT_ACTION":
            if self._pending_night and not self._pending_night.done():
                self._pending_night.set_result(payload)
            else:
                await self._send_error(websocket, "NOT_NIGHT_PHASE", "当前不需要夜晚行动")
            return

        if event_type == "ACK_SEER_CHECK_RESULT":
            if self._pending_seer_ack and not self._pending_seer_ack.done():
                self._pending_seer_ack.set_result(None)
            return

        await self._send_error(websocket, "UNKNOWN_EVENT", f"未知事件 {event_type}")

    async def _send_error(self, websocket: WebSocket, code: str, message: str) -> None:
        await self.connections.send_to(
            websocket, {"type": "ERROR", "payload": {"code": code, "message": message}}
        )

    async def _send_initial_events(self, websocket: WebSocket) -> None:
        await self.connections.send_to(
            websocket,
            {
                "type": "CONNECTED",
                "payload": {"game_id": self.game_id, "message": "WebSocket 已连接"},
            },
        )
        deadline = self._game_started_at + settings.game_max_duration_seconds
        await self.connections.send_to(
            websocket,
            {
                "type": "GAME_STARTED",
                "payload": {
                    "your_role": self.human_role.value,
                    "your_seat": self.human_seat,
                    "game_deadline_ts": deadline,
                    "players": [
                        {
                            "seat": p.seat,
                            "name": p.name,
                            "is_alive": p.is_alive,
                            "is_human": p.is_human,
                        }
                        for p in self.state.players
                    ],
                },
            },
        )
        entered_night = await self._broadcast_phase_changed()
        if entered_night:
            asyncio.get_running_loop().create_task(self._delayed_sub_phase_cue(2.2))
        else:
            await self._broadcast_sub_phase_cue()
        await self._broadcast_new_logs()
        await self._broadcast_snapshot()
        await self._emit_llm_traces(self.human_seat, start=0)

    async def _emit_llm_traces(self, target_seat: int, start: int | None = None) -> None:
        """向指定座位推送 LLM 追溯（含完整 messages，供调试小窗展示）。"""
        begin = self._last_trace_index if start is None else start
        for t in self.state.llm_traces[begin:]:
            player = self.state.get_player(t.player_seat)
            role = player.role.value if player.role else "unknown"
            await self.connections.send_to_seat(
                target_seat,
                {
                    "type": "LLM_TRACE",
                    "payload": {
                        "trace_id": t.id,
                        "player_seat": t.player_seat,
                        "role": role,
                        "step": t.step,
                        "phase_ref": t.phase_ref,
                        "messages": t.messages_full,
                        "response": t.response_summary,
                        "strategy_id": t.strategy_id,
                        "timestamp": t.timestamp.isoformat(),
                    },
                },
            )
        if target_seat == self.human_seat:
            self._last_trace_index = len(self.state.llm_traces)

    async def _run(self) -> None:
        try:
            while self.connections.count > 0 and self.state.phase != Phase.GAME_OVER:
                if self._check_game_timeout():
                    break
                progressed = await self._tick()
                if not progressed:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.05)
            if self.state.phase == Phase.GAME_OVER:
                await self._broadcast_game_over()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await self.connections.broadcast(
                {"type": "ERROR", "payload": {"code": "LOOP_ERROR", "message": str(exc)}}
            )

    def _check_game_timeout(self) -> bool:
        if self._timeout_handled or self.state.phase == Phase.GAME_OVER:
            return self.state.phase == Phase.GAME_OVER
        if time.time() >= self._game_started_at + settings.game_max_duration_seconds:
            self._timeout_handled = True
            asyncio.get_running_loop().create_task(self._force_game_timeout())
            return True
        return False

    async def _force_game_timeout(self) -> None:
        if self.state.phase == Phase.GAME_OVER:
            return
        self.state.phase = Phase.GAME_OVER
        self.state.status = GameStatus.FINISHED
        if self.state.winner is None:
            self.state.winner = Faction.VILLAGE
        await self.connections.broadcast(
            {
                "type": "GAME_TIMEOUT",
                "payload": {
                    "message": f"对局已达 {settings.game_max_duration_seconds // 60} 分钟上限，自动结束",
                },
            }
        )
        await self._broadcast_game_over()

    async def _tick(self) -> bool:
        if self.state.phase == Phase.GAME_OVER:
            return False

        engine = self._engine

        if engine._should_auto_skip_sub_phase():
            engine.advance_phase()
            await self._on_phase_advanced()
            return True

        sub = self.state.sub_phase

        if self.state.phase == Phase.NIGHT or sub == SubPhase.HUNTER_SHOOT:
            return await self._tick_night()

        if sub == SubPhase.DAY_SPEECH:
            return await self._tick_speech()

        if sub == SubPhase.DAY_VOTE:
            return await self._tick_vote()

        if engine.is_sub_phase_complete():
            engine.advance_phase()
            await self._on_phase_advanced()
            return True

        return False

    async def _tick_night(self) -> bool:
        engine = self._engine
        sub = self.state.sub_phase

        if self._pending_seer_ack is not None and not self._pending_seer_ack.done():
            return False

        if sub == SubPhase.NIGHT_RESOLVE:
            await self._await_round_memory_compression()
            engine.advance_phase()
            await self._on_phase_advanced()
            return True

        async def _run_ai_night() -> None:
            await submit_night_for_ai(
                engine, self.human_seat, send_private=self._send_private_to_seat
            )
            await self._emit_llm_traces(self.human_seat)
            await self._broadcast_wolf_nominations_to_human_wolf()

        # 仅对当前子阶段提交 AI 行动
        await _run_ai_night()

        human_need = needs_human_night_action(self.state, self.human_seat)
        if human_need:
            if self._pending_night is None or self._pending_night.done():
                self._pending_night = asyncio.get_running_loop().create_future()
                witch_info = {}
                if human_need[0] == "witch_action":
                    from app.game.night_resolution import ensure_wolf_kill_target

                    ensure_wolf_kill_target(self.state, self._engine.rng)
                    witch_info = {
                        "wolf_kill_victim": self.state.wolf_kill_target,
                        "heal_available": self.state.witch_state.heal_available,
                        "heal_used": self.state.night_actions.witch_heal_target is not None,
                        "poison_available": self.state.witch_state.poison_available,
                        "poison_used": self.state.night_actions.witch_poison_target is not None,
                        "potion_used_tonight": (
                            self.state.night_actions.witch_heal_target is not None
                            or self.state.night_actions.witch_poison_target is not None
                        ),
                    }
                wolf_info = {}
                if human_need[0] == "wolf_nominate":
                    wolf_info = {
                        "wolf_nominations": dict(self.state.night_actions.wolf_nominations),
                        "wolf_teammates": [
                            w.seat
                            for w in self.state.alive_wolves()
                            if w.seat != self.human_seat
                        ],
                    }
                await self.connections.send_to_seat(
                    self.human_seat,
                    {
                        "type": "NIGHT_ACTION_REQUEST",
                        "payload": {
                            "action_type": human_need[0],
                            "actor_seat": self.human_seat,
                            "alive_seats": sorted(self.state.alive_seats),
                            **witch_info,
                            **wolf_info,
                        },
                    },
                )
            try:
                payload = await asyncio.wait_for(
                    self._pending_night, timeout=settings.game_night_action_timeout_seconds
                )
            except asyncio.TimeoutError:
                payload = None
            self._pending_night = None
            if payload:
                msg = self._apply_night_payload(payload)
                await self._send_action_ack(
                    self.human_seat,
                    "night",
                    msg or "夜晚行动已提交",
                )
                if (
                    payload.get("action_type") == "seer_check"
                    and self.state.sub_phase == SubPhase.NIGHT_SEER
                    and self.state.night_actions.seer_check_target is not None
                ):
                    await self._present_human_seer_result()
                await self._broadcast_wolf_nominations_to_human_wolf()
            else:
                auto_submit_human_night(engine, self.human_seat)
                await self._send_action_ack(
                    self.human_seat,
                    "night",
                    "操作超时，已自动跳过",
                    success=False,
                )
                if (
                    sub == SubPhase.NIGHT_SEER
                    and self.state.night_actions.seer_check_target is not None
                ):
                    await self._present_human_seer_result()

            # 人类提交后补跑当前子阶段剩余 AI（如人类狼刀后其余狼）
            if self.state.sub_phase == sub and not engine.is_sub_phase_complete():
                await _run_ai_night()

        # 严格单步：子阶段未变且已完成才推进，不在同一 tick 进入下一子阶段
        if self.state.sub_phase != sub or not engine.is_sub_phase_complete():
            return False

        engine.advance_phase()
        await self._on_phase_advanced()
        return True

    def _start_round_memory_compression(self) -> None:
        """入夜后异步压缩刚结束的白日公屏"""
        if self._memory_compress_task and not self._memory_compress_task.done():
            return
        from_index = self.state.current_round_log_start_index
        if from_index >= len(self.state.public_log):
            return
        self._memory_compress_from_index = from_index
        self._memory_compress_day = max(1, self.state.day_number)
        state = self.state
        day = self._memory_compress_day

        async def _run() -> str:
            return await run_compression_task(state, from_index, day)

        self._memory_compress_task = asyncio.create_task(_run())

    async def _await_round_memory_compression(self) -> None:
        """天亮前合并压缩摘要"""
        if self._memory_compress_task is None:
            return
        try:
            summary = await self._memory_compress_task
        except Exception:
            from app.ai.memory_compress import summarize_public_log_rule_based

            entries = self.state.public_log[self._memory_compress_from_index :]
            summary = summarize_public_log_rule_based(
                entries, day_number=self._memory_compress_day
            )
        self._memory_compress_task = None
        apply_round_compression(self.state, summary)

    async def _present_human_seer_result(self) -> None:
        """人类预言家验人后展示结果并阻塞至确认"""
        target = self.state.night_actions.seer_check_target
        if target is None:
            return
        resolve_seer_check(self.state)
        is_wolf = seer_check_is_wolf(self.state, target)
        record_seer_check_truth(self.state, self.human_seat, target, is_wolf)
        self._pending_seer_ack = asyncio.get_running_loop().create_future()
        await self.connections.send_to_seat(
            self.human_seat,
            {
                "type": "SEER_CHECK_RESULT",
                "payload": {
                    "target_seat": target,
                    "is_wolf": is_wolf,
                    "result_label": "狼" if is_wolf else "好人",
                },
            },
        )
        try:
            await asyncio.wait_for(self._pending_seer_ack, timeout=120.0)
        except asyncio.TimeoutError:
            pass
        self._pending_seer_ack = None

    def _apply_night_payload(self, payload: dict[str, Any]) -> str:
        engine = self._engine
        action_type = payload.get("action_type", "")
        target = payload.get("target_seat")
        if target is not None:
            target = int(target)
        seat = self.human_seat
        last: ApplyResult | None = None

        mapping = {
            "wolf_nominate": ActionType.WOLF_NOMINATE,
            "seer_check": ActionType.SEER_CHECK,
            "guard_protect": ActionType.GUARD_PROTECT,
            "witch_heal": ActionType.WITCH_HEAL,
            "witch_poison": ActionType.WITCH_POISON,
            "hunter_shoot": ActionType.HUNTER_SHOOT,
        }
        if action_type == "witch_action":
            if payload.get("use_heal") and payload.get("use_poison"):
                last = ApplyResult(False, "每夜最多使用一瓶药水")
                return last.message
            if payload.get("use_heal"):
                last = engine.apply_action(
                    Action(action_type=ActionType.WITCH_HEAL, actor_seat=seat, target_seat=target)
                )
            elif payload.get("use_poison") and target:
                last = engine.apply_action(
                    Action(action_type=ActionType.WITCH_POISON, actor_seat=seat, target_seat=target)
                )
            else:
                last = engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=seat))
            return last.message if last else "女巫行动已记录"

        if action_type == "pass" or action_type == "skip":
            last = engine.apply_action(Action(action_type=ActionType.PASS, actor_seat=seat))
            return last.message if last else "已跳过"

        at = mapping.get(action_type)
        if at:
            last = engine.apply_action(Action(action_type=at, actor_seat=seat, target_seat=target))
        return last.message if last else "行动已提交"

    async def _tick_speech(self) -> bool:
        engine = self._engine
        state = self.state

        if not state.speech_order or state.current_speaker_index >= len(state.speech_order):
            if engine.is_sub_phase_complete():
                engine.advance_phase()
                await self._on_phase_advanced()
            return True

        seat = state.speech_order[state.current_speaker_index]
        player = state.get_player(seat)

        if not player.is_alive:
            state.current_speaker_index += 1
            return True

        if self._current_speech_seat != seat:
            self._current_speech_seat = seat
            deadline = time.time() + self._speech_seconds()
            await self.connections.broadcast(
                {
                    "type": "SPEAK_TURN_START",
                    "payload": {
                        "seat": seat,
                        "deadline_ts": deadline,
                        "is_you": seat == self.human_seat,
                    },
                }
            )

            if player.is_human:
                self._pending_speech = asyncio.get_running_loop().create_future()
                try:
                    content = await asyncio.wait_for(
                        self._pending_speech, timeout=float(self._speech_seconds())
                    )
                except asyncio.TimeoutError:
                    content = ""
                self._pending_speech = None
                engine.apply_action(
                    Action(
                        action_type=ActionType.SPEECH,
                        actor_seat=seat,
                        content=content or "（超时跳过）",
                    )
                )
            else:
                await asyncio.sleep(0.3)
                on_stream_delta = None
                if is_llm_enabled():

                    async def on_stream_delta(delta: str, _seat: int = seat) -> None:
                        await self.connections.broadcast(
                            {
                                "type": "SPEECH_STREAM_DELTA",
                                "payload": {"seat": _seat, "delta": delta},
                            }
                        )

                    await self.connections.broadcast(
                        {
                            "type": "SPEECH_STREAM_START",
                            "payload": {"seat": seat},
                        }
                    )
                await submit_speech(engine, seat, on_stream_delta=on_stream_delta)
                await self._emit_llm_traces(self.human_seat)
                if is_llm_enabled():
                    await self.connections.broadcast(
                        {
                            "type": "SPEECH_STREAM_END",
                            "payload": {"seat": seat},
                        }
                    )

            await self.connections.broadcast(
                {"type": "SPEAK_TURN_END", "payload": {"seat": seat}}
            )
            self._current_speech_seat = None
            await self._broadcast_new_logs()

        if engine.is_sub_phase_complete():
            engine.advance_phase()
            await self._on_phase_advanced()
            return True

        return True

    async def _tick_vote(self) -> bool:
        engine = self._engine
        state = self.state
        human = state.get_player(self.human_seat)

        if not self._vote_started:
            self._vote_started = True
            self._vote_ai_batch_done = False
            await self.connections.broadcast(
                {
                    "type": "VOTE_STARTED",
                    "payload": {"candidates": sorted(state.alive_seats)},
                }
            )
            if human.is_alive and not any(v.voter_seat == self.human_seat for v in state.day_votes):
                self._pending_vote = asyncio.get_running_loop().create_future()

        voted = {v.voter_seat for v in state.day_votes}

        if not self._vote_ai_batch_done:
            ai_seats = [
                s
                for s in sorted(state.alive_seats)
                if s not in voted and not state.get_player(s).is_human
            ]
            if ai_seats:
                await asyncio.gather(*[submit_vote(engine, s) for s in ai_seats])
            await self._emit_llm_traces(self.human_seat)
            self._vote_ai_batch_done = True

        if (
            human.is_alive
            and self.human_seat not in voted
            and not any(v.voter_seat == self.human_seat for v in state.day_votes)
        ):
            if self._pending_vote is None or self._pending_vote.done():
                self._pending_vote = asyncio.get_running_loop().create_future()
            if not self._pending_vote.done():
                try:
                    await asyncio.wait_for(self._pending_vote, timeout=60.0)
                except asyncio.TimeoutError:
                    if not any(
                        v.voter_seat == self.human_seat for v in state.day_votes
                    ):
                        result = engine.apply_action(
                            Action(
                                action_type=ActionType.VOTE,
                                actor_seat=self.human_seat,
                                target_seat=None,
                            )
                        )
                        await self._send_action_ack(
                            self.human_seat,
                            "vote",
                            result.message or "超时弃票",
                            success=result.ok,
                        )
            self._pending_vote = None

        if engine.is_sub_phase_complete():
            self._vote_started = False
            self._vote_ai_batch_done = False
            self._pending_vote = None
            engine.advance_phase()
            await self._on_phase_advanced()
            await self._broadcast_vote_result()
            return True

        return True

    async def _broadcast_wolf_nominations_to_human_wolf(self) -> None:
        if self.state.sub_phase != SubPhase.NIGHT_WOLF:
            return
        player = self.state.get_player(self.human_seat)
        if not player.is_alive or player.role != Role.WOLF:
            return
        await self.connections.send_to_seat(
            self.human_seat,
            {
                "type": "WOLF_NOMINATION_UPDATE",
                "payload": {
                    "nominations": dict(self.state.night_actions.wolf_nominations),
                    "teammates": [
                        w.seat
                        for w in self.state.alive_wolves()
                        if w.seat != self.human_seat
                    ],
                },
            },
        )

    async def _maybe_notify_wolf_kill_result(self) -> None:
        if self.state.sub_phase != SubPhase.NIGHT_RESOLVE:
            return
        if self.state.wolf_kill_target is None:
            return
        night_key = self.state.day_number
        if self._wolf_kill_result_sent_for_night == night_key:
            return
        player = self.state.get_player(self.human_seat)
        if not player.is_alive or player.role != Role.WOLF:
            return

        from collections import Counter

        nominations = self.state.night_actions.wolf_nominations
        counts = Counter(nominations.values())
        max_votes = max(counts.values()) if counts else 0
        top_targets = [t for t, c in counts.items() if c == max_votes]
        is_tie = len(top_targets) >= 2

        self._wolf_kill_result_sent_for_night = night_key
        await self.connections.send_to_seat(
            self.human_seat,
            {
                "type": "WOLF_KILL_RESULT",
                "payload": {
                    "kill_target": self.state.wolf_kill_target,
                    "nominations": dict(nominations),
                    "is_tie": is_tie,
                    "tied_targets": top_targets if is_tie else [],
                },
            },
        )

    async def _send_private_to_seat(self, seat: int, event: dict[str, Any]) -> None:
        await self.connections.send_to_seat(seat, event)

    async def _on_phase_advanced(self) -> None:
        await self._maybe_notify_wolf_kill_result()
        await self._maybe_enter_spectator_mode()
        entered_night = await self._broadcast_phase_changed()
        if entered_night:
            asyncio.get_running_loop().create_task(self._delayed_sub_phase_cue(2.2))
        else:
            await self._broadcast_sub_phase_cue()
        await self._broadcast_new_logs()
        await self._broadcast_snapshot()

    async def _delayed_sub_phase_cue(self, delay: float) -> None:
        await asyncio.sleep(delay)
        if self.state.phase == Phase.GAME_OVER:
            return
        await self._broadcast_sub_phase_cue()

    async def _maybe_enter_spectator_mode(self) -> None:
        human = self.state.get_player(self.human_seat)
        if human.is_alive or self._spectator_sent:
            return
        self._spectator_sent = True
        await self.connections.send_to_seat(
            self.human_seat,
            {
                "type": "SPECTATOR_MODE",
                "payload": {
                    "message": "你已出局，可观战；完整复盘见局后",
                    "can_view_private": True,
                },
            },
        )

    async def _broadcast_phase_changed(self) -> bool:
        """返回是否刚进入夜晚（需先播「天黑请闭眼」）。"""
        key = (self.state.phase, self.state.sub_phase, self.state.day_number)
        if key == self._last_phase_key:
            return False
        prev_key = self._last_phase_key
        self._last_phase_key = key
        await self.connections.broadcast(
            {
                "type": "PHASE_CHANGED",
                "payload": {
                    "phase": self.state.phase.value,
                    "day_number": self.state.day_number,
                    "sub_phase": self.state.sub_phase.value if self.state.sub_phase else None,
                },
            }
        )
        entered_night = self.state.phase == Phase.NIGHT and (
            prev_key is None or prev_key[0] != Phase.NIGHT
        )
        if entered_night:
            self._start_round_memory_compression()
            await self._broadcast_night_fall_cue()
        return entered_night

    async def _broadcast_night_fall_cue(self) -> None:
        """仅刚进入夜晚时：天黑请闭眼"""
        await self.connections.broadcast(
            {
                "type": "SUB_PHASE_CUE",
                "payload": {
                    "cue_kind": "night_fall",
                    "sub_phase": self.state.sub_phase.value
                    if self.state.sub_phase
                    else SubPhase.NIGHT_WOLF.value,
                    "day_number": self.state.day_number,
                    "active_role": None,
                },
            }
        )

    async def _broadcast_sub_phase_cue(self) -> None:
        sub = self.state.sub_phase
        if sub is None or sub == SubPhase.NIGHT_RESOLVE:
            return
        active_role = self._SUB_PHASE_ACTIVE_ROLE.get(sub)
        if active_role is not None:
            cue_kind = "night_wake"
        elif sub == SubPhase.HUNTER_SHOOT:
            cue_kind = "hunter_wake"
        else:
            return
        await self.connections.broadcast(
            {
                "type": "SUB_PHASE_CUE",
                "payload": {
                    "cue_kind": cue_kind,
                    "sub_phase": sub.value,
                    "day_number": self.state.day_number,
                    "active_role": active_role.value if active_role else None,
                },
            }
        )

    async def _broadcast_new_logs(self) -> None:
        logs = self.state.public_log[self._last_log_index :]
        for entry in logs:
            await self.connections.broadcast(
                {
                    "type": "PUBLIC_LOG",
                    "payload": {
                        "entry": {
                            "id": entry.id,
                            "type": entry.type,
                            "seat": entry.seat,
                            "content": entry.content,
                            "timestamp": entry.timestamp.isoformat(),
                        }
                    },
                }
            )
        self._last_log_index = len(self.state.public_log)

    async def _broadcast_snapshot(self) -> None:
        base = self._build_snapshot()

        def payload_for(seat: int | None) -> dict[str, Any]:
            if seat is None:
                return base
            return filter_snapshot_for_player(base, self.state, seat)

        await self.connections.broadcast_except_payload(
            {"type": "STATE_SNAPSHOT"}, payload_for
        )

    def _build_snapshot(self) -> dict[str, Any]:
        speech_turn = None
        if self.state.sub_phase == SubPhase.DAY_SPEECH and self._current_speech_seat:
            speech_turn = {
                "seat": self._current_speech_seat,
                "is_you": self._current_speech_seat == self.human_seat,
            }
        return {
            "phase": self.state.phase.value,
            "sub_phase": self.state.sub_phase.value if self.state.sub_phase else None,
            "day_number": self.state.day_number,
            "players": [
                {
                    "seat": p.seat,
                    "name": p.name,
                    "is_alive": p.is_alive,
                    "is_human": p.is_human,
                }
                for p in self.state.players
            ],
            "public_log": [
                {
                    "id": e.id,
                    "type": e.type,
                    "seat": e.seat,
                    "content": e.content,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self.state.public_log
            ],
            "speech_turn": speech_turn,
            "vote_active": self.state.sub_phase == SubPhase.DAY_VOTE,
            "winner": self.state.winner.value if self.state.winner else None,
        }

    async def _broadcast_vote_result(self) -> None:
        from collections import Counter

        tally: dict[int, int] = Counter()
        for v in self.state.day_votes:
            if v.target_seat is not None:
                tally[v.target_seat] += 1
        await self.connections.broadcast(
            {
                "type": "VOTE_RESULT",
                "payload": {
                    "tally": dict(tally),
                    "eliminated_seat": self.state.last_exiled_seat,
                    "is_tie": self.state.last_exiled_seat is None
                    and len(self.state.day_votes) > 0
                    and not tally,
                },
            }
        )

    async def _broadcast_game_over(self) -> None:
        if self._game_over_broadcast:
            return
        self._game_over_broadcast = True
        self.state.status = GameStatus.FINISHED
        token = game_registry.get_token(self.game_id) or ""
        try:
            replay_store.save(self.game_id, self.state, self.human_seat, token)
        except Exception:
            pass
        winner = self.state.winner.value if self.state.winner else "unknown"
        await self.connections.broadcast(
            {
                "type": "GAME_END",
                "payload": {
                    "winner": winner,
                    "replay_url": f"/replay/{self.game_id}",
                },
            }
        )


class GameLoopRegistry:
    """全局 GameLoop 实例管理"""

    def __init__(self) -> None:
        self._loops: dict[str, GameLoop] = {}

    def get_or_create(
        self,
        game_id: str,
        state: GameState,
        human_seat: int,
        human_role: Role,
    ) -> GameLoop:
        if game_id not in self._loops:
            self._loops[game_id] = GameLoop(game_id, state, human_seat, human_role)
        return self._loops[game_id]

    def get(self, game_id: str) -> GameLoop | None:
        return self._loops.get(game_id)


game_loop_registry = GameLoopRegistry()
