"""Phase 3：人格、策略库、记忆、LLM 客户端、降级"""

from __future__ import annotations

import json
import random
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.memory import (
    ensure_player_memory,
    format_memory_for_prompt,
    record_public_claim,
    record_strategy_usage,
)
from app.ai.orchestrator import is_llm_enabled, submit_speech
from app.ai.personality import assign_personalities_to_ai, load_personality_templates
from app.ai.strategy_library import get_candidates_for_role, select_strategy_weighted
from app.config import settings
from app.game.dealing import setup_game
from app.game.engine import create_engine
from app.llm.client import LlmNotConfiguredError, QwenClient, get_qwen_client
from app.llm.pipeline import LlmPipeline
from app.models.game import GameState, Phase, Player, Role, SubPhase
from app.services.state_view import build_public_view


def _empty_state() -> GameState:
    return GameState(game_id="t", phase=Phase.SETUP, players=[], alive_seats=set())


def test_personality_templates_at_least_nine() -> None:
    templates = load_personality_templates()
    assert len(templates) >= 9


def test_assign_personalities_no_duplicate() -> None:
    state = GameState(
        game_id="p1",
        phase=Phase.NIGHT,
        players=[
            Player(seat=i, name=f"AI-{i}", is_human=False, role=Role.VILLAGER)
            for i in range(1, 10)
        ],
        alive_seats=set(range(1, 10)),
    )
    assign_personalities_to_ai(state, random.Random(1))
    ids = [state.personality_by_seat[s]["id"] for s in range(1, 10)]
    assert len(ids) == len(set(ids))


def test_strategy_library_loads_per_role() -> None:
    for role in (Role.WOLF, Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.VILLAGER):
        candidates = get_candidates_for_role(role)
        assert 5 <= len(candidates) <= 10
        assert candidates[0].id


def test_strategy_weighted_selection() -> None:
    state = _empty_state()
    state.player_memories[3] = ensure_player_memory(state, 3)
    entry, reason = select_strategy_weighted(
        state, 3, Role.WOLF, {"decision_bias": "fake_claim"}, random.Random(99)
    )
    assert entry.role == "wolf"
    assert reason


def test_memory_prompt_injection() -> None:
    state = _empty_state()
    record_strategy_usage(state, 2, "W01", "深水")
    record_public_claim(state, 2, "role_claim", "我是预言家", is_truthful=False)
    text = format_memory_for_prompt(state, 2)
    assert "W01" in text
    assert "预言家" in text


def test_state_view_hides_other_roles() -> None:
    engine = create_engine(GameState(game_id="v", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "测试", seed=100)
    human_seat = next(p.seat for p in engine.state.players if p.is_human)
    view = build_public_view(engine.state, human_seat)
    assert view["your_seat"] == human_seat
    assert "your_role" in view
    assert "wolf_teammates" in view or view["your_role"] != "wolf"


def test_state_view_hides_wolf_nominations() -> None:
    engine = create_engine(GameState(game_id="v2", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "测试", seed=101)
    wolf = next(p for p in engine.state.players if p.role == Role.WOLF)
    engine.state.night_actions.wolf_nominations = {wolf.seat: 5, 6: 5}
    view = build_public_view(engine.state, wolf.seat)
    assert "wolf_nominations" not in view


def test_state_view_includes_speech_phase_during_day_speech() -> None:
    engine = create_engine(GameState(game_id="speech", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "发言顺序", seed=55)
    state = engine.state
    state.phase = Phase.DAY
    state.sub_phase = SubPhase.DAY_SPEECH
    state.speech_order = [5, 8, 9]
    state.current_speaker_index = 2  # 9 号即将发言，5/8 已过麦

    view = build_public_view(state, 9)
    speech = view.get("speech_phase")
    assert speech is not None
    assert speech["speech_order"] == [5, 8, 9]
    assert speech["already_spoken_seats"] == [5, 8]
    assert speech["current_speaker_seat"] == 9
    assert speech["pending_speaker_seats"] == []
    assert speech["speech_status_by_seat"] == {5: "done", 8: "done", 9: "current"}
    assert speech["is_your_turn"] is True
    assert "5" in speech["summary"] and "8" in speech["summary"]


def test_build_speech_messages_includes_sequential_turn_rules() -> None:
    from app.ai.strategy_library import get_candidates_for_role
    from app.llm import prompts

    engine = create_engine(GameState(game_id="speech-prompt", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "发言规则", seed=56)
    state = engine.state
    state.phase = Phase.DAY
    state.sub_phase = SubPhase.DAY_SPEECH
    state.speech_order = [5, 8, 9]
    state.current_speaker_index = 2

    view = build_public_view(state, 9)
    role = state.get_player(9).role or Role.VILLAGER
    strategy = get_candidates_for_role(role)[0]
    messages = prompts.build_speech_messages(
        state, 9, role, view, strategy, "暂无疑点", "冷静型", 40, 200
    )
    user_content = messages[1]["content"]
    assert "发言顺序规则" in user_content
    assert "5号" in user_content and "8号" in user_content
    assert "不可再开口" in user_content or "不能再开口" in user_content
    assert "你怎么不表态" in user_content


def test_state_view_no_speech_phase_outside_day_speech() -> None:
    engine = create_engine(GameState(game_id="nospeech", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "非发言", seed=57)
    state = engine.state
    state.phase = Phase.DAY
    state.sub_phase = SubPhase.DAY_VOTE
    state.speech_order = [1, 2, 3]
    view = build_public_view(state, 1)
    assert "speech_phase" not in view


def test_wolf_nominate_pipeline_seat_rng_is_int() -> None:
    """狼刀 pipeline 座位 RNG 使用合法 int 种子。"""
    state = GameState(game_id="wolf-seed", seed=42, day_number=0, alive_seats=set())
    seat = 3
    seat_rng = random.Random(
        hash((state.seed, seat, state.day_number, 7919)) & 0xFFFFFFFF
    )
  # 若传入 tuple 会抛 TypeError
    assert isinstance(seat_rng.random(), float)


@pytest.mark.asyncio
async def test_wolf_nominate_pipeline_runs_with_valid_seed() -> None:
    engine = create_engine(GameState(game_id="wolf-seed", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "测试", seed=42)
    wolf = next(p for p in engine.state.players if p.role == Role.WOLF)

    pipe = LlmPipeline.__new__(LlmPipeline)
    pipe.decide_action = AsyncMock(return_value={"action_type": "wolf_nominate", "target_seat": 5})

    candidates = [s for s in engine.state.alive_seats if s != wolf.seat]
    result = await LlmPipeline.run_wolf_nominate_pipeline(
        pipe, engine.state, wolf.seat, "{}", candidates, engine.rng
    )
    assert result["target_seat"] == 5


def test_wolf_nominate_extra_mentions_independence() -> None:
    from app.llm import prompts

    text = prompts.build_wolf_nominate_extra(3, [1, 5, 7], {"aggression": 0.7, "decision_bias": "push_vote"})
    assert "3" in text
    assert "独立" in text or "不同" in text


def test_get_qwen_client_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qwen_api_key", "")
    monkeypatch.setattr(settings, "dashscope_api_key", "")
    assert get_qwen_client() is None
    assert is_llm_enabled() is False


@pytest.mark.asyncio
async def test_qwen_client_raises_without_key() -> None:
    client = QwenClient(api_key="")
    with pytest.raises(LlmNotConfiguredError):
        await client.chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_pipeline_select_strategy_mock_http(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(GameState(game_id="llm", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "LLM", seed=7)
    ai_seat = next(p.seat for p in engine.state.players if not p.is_human)
    ai = engine.state.get_player(ai_seat)
    role = ai.role or Role.VILLAGER

    mock_response = json.dumps({"strategy_id": "V01", "reason": "盘逻辑"})
    client = QwenClient(api_key="test-key")
    client.chat = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

    pipe = LlmPipeline(client)
    from app.services.state_view import build_state_view_text

    view = build_state_view_text(engine.state, ai_seat)
    entry, reason = await pipe.select_strategy(engine.state, ai_seat, role, view, engine.rng)
    assert entry.id == "V01"
    assert "盘逻辑" in reason or reason
    assert len(engine.state.llm_traces) >= 1


@pytest.mark.asyncio
async def test_orchestrator_fallback_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qwen_api_key", "")
    monkeypatch.setattr(settings, "dashscope_api_key", "")
    engine = create_engine(GameState(game_id="fb", phase=Phase.SETUP, players=[], alive_seats=set()))
    setup_game(engine.state, "降级", seed=12)
    ai_seat = next(p.seat for p in engine.state.players if not p.is_human)
    engine.state.phase = Phase.DAY
    engine.state.sub_phase = SubPhase.DAY_SPEECH
    engine.state.speech_order = [ai_seat]
    engine.state.current_speaker_index = 0
    await submit_speech(engine, ai_seat)
    assert ai_seat in engine.state.speeches or any(
        e.seat == ai_seat and e.type == "speech" for e in engine.state.public_log
    )


@pytest.mark.asyncio
async def test_llm_client_http_mock() -> None:
    client = QwenClient(api_key="sk-test", model="qwen-turbo")

    class FakeResp:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "你好"}}]}

    with patch("httpx.AsyncClient") as mock_cls:
        instance = mock_cls.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=FakeResp())
        out = await client.chat([{"role": "user", "content": "test"}])
    assert out == "你好"
