"""记忆压缩单元测试"""

from app.ai.memory_compress import (
    apply_round_compression,
    format_public_memory_text,
    summarize_public_log_rule_based,
)
from app.models.game import PublicLogEntry


def test_rule_based_summary() -> None:
    entries = [
        PublicLogEntry(
            id="1",
            phase_ref="day1_speech",
            type="speech",
            seat=2,
            content="我是好人",
            timestamp=__import__("datetime").datetime.utcnow(),
        ),
        PublicLogEntry(
            id="2",
            phase_ref="day1_system",
            type="system",
            seat=None,
            content="昨晚是平安夜",
            timestamp=__import__("datetime").datetime.utcnow(),
        ),
    ]
    text = summarize_public_log_rule_based(entries, day_number=1)
    assert "第1天" in text
    assert "发言" in text or "2号" in text


def test_apply_compression_updates_state() -> None:
    from app.game.dealing import setup_game
    from app.models.game import GameState

    state = GameState(game_id="t", seed=1, alive_seats=set())
    setup_game(state, "玩家", 1)
    state.public_log.append(
        PublicLogEntry(
            id="a",
            phase_ref="d1",
            type="system",
            seat=None,
            content="测试",
            timestamp=__import__("datetime").datetime.utcnow(),
        )
    )
    apply_round_compression(state, "第1天摘要")
    assert state.round_memory_summaries == ["第1天摘要"]
    assert state.current_round_log_start_index == 1
    text = format_public_memory_text(state)
    assert "第1天" in text
