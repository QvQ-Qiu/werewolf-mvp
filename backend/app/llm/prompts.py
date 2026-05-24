"""LLM Prompt 模板（策略选 → 行动 → 发言）"""

from __future__ import annotations

from typing import Any

from app.ai.belief import belief_to_json
from app.ai.memory import format_memory_for_prompt
from app.ai.memory_compress import format_public_memory_text
from app.ai.personality import format_personality_block
from app.ai.strategy_library import StrategyEntry
from app.models.game import GameState, Role


def _role_label(role: Role) -> str:
    labels = {
        Role.WOLF: "狼人",
        Role.SEER: "预言家",
        Role.WITCH: "女巫",
        Role.HUNTER: "猎人",
        Role.GUARD: "守卫",
        Role.VILLAGER: "村民",
    }
    return labels.get(role, role.value)


def build_system_base(
    seat: int,
    role: Role,
    day_number: int,
    phase_label: str,
    personality_block: str,
) -> str:
    return f"""你是十人狼人杀局中 {seat} 号玩家，身份为{_role_label(role)}。
当前：第 {day_number} 天，阶段 {phase_label}。

【人格与文风】
{personality_block}

【硬性规则】
- 只能依据下方「合法信息」推理与决策，禁止开天眼。
- 可以说谎，但必须服务于当前策略的战术目的。
- 禁止与已记录的公开承诺矛盾（除非策略明确为改口且需解释）。
- 禁止无目的废话、编造不可能知道的信息。
"""


def build_strategy_select_messages(
    state: GameState,
    seat: int,
    role: Role,
    state_view: dict[str, Any],
    candidates: list[StrategyEntry],
    personality_block: str,
) -> list[dict[str, str]]:
    phase_label = f"{state.phase.value}/{state.sub_phase.value if state.sub_phase else ''}"
    cand_text = "\n".join(
        f"- {s.id}: {s.name}（{s.prompt_hint}，倾向权重 {s.weight}）" for s in candidates
    )
    memory_block = format_memory_for_prompt(state, seat)
    user = f"""【合法信息】
{state_view}

【策略历史与公开承诺】
{memory_block}

【候选策略（仅选一条）】
{cand_text}

请从候选策略中选择最适合当前局势的一条。
严格输出 JSON，不要 markdown：
{{"strategy_id": "策略ID", "reason": "一句话理由"}}"""
    return [
        {
            "role": "system",
            "content": build_system_base(
                seat, role, state.day_number, phase_label, personality_block
            ),
        },
        {"role": "user", "content": user},
    ]


def build_wolf_nominate_extra(
    seat: int,
    candidates: list[int],
    personality: dict[str, Any],
) -> str:
    """狼刀提名：强调各狼独立决策，避免并行 LLM 输出趋同。"""
    bias = personality.get("decision_bias", "neutral")
    aggression = float(personality.get("aggression", 0.5))
    if aggression >= 0.65:
        style = "优先刀发言活跃、威胁大的好人"
    elif aggression <= 0.35:
        style = "优先使用偏保守的刀口，避免过于显眼"
    else:
        style = "综合局势选择刀口"
    bias_hint = {
        "push_vote": "你倾向主动带刀，可刀关键位",
        "follow_majority": "你倾向稳妥，可刀边缘位",
        "fake_claim": "考虑刀可能跳神的好人",
    }.get(bias, style)
    return (
        f"【狼刀独立决策】你是 {seat} 号狼，本回合仅提交你的个人提名。"
        f"你看不到队友此刻的提名，队友也可能与你不同。"
        f"可选刀口：{candidates}。你的倾向：{bias_hint}。"
        f"请按你的人格与策略做出独立判断，不必与队友一致。"
    )


def build_action_decide_messages(
    state: GameState,
    seat: int,
    role: Role,
    state_view: dict[str, Any],
    strategy: StrategyEntry,
    action_schema: str,
    personality_block: str,
    extra_instructions: str = "",
) -> list[dict[str, str]]:
    phase_label = f"{state.phase.value}/{state.sub_phase.value if state.sub_phase else ''}"
    memory_block = format_memory_for_prompt(state, seat)
    extra_block = f"\n\n{extra_instructions}" if extra_instructions else ""
    user = f"""【当前策略】{strategy.id} - {strategy.name}
{strategy.prompt_hint}

【合法信息】
{state_view}

【记忆】
{memory_block}

【可选行动】
{action_schema}

请做出本回合行动决策。{extra_block}
严格输出 JSON：
{{"action_type": "类型", "target_seat": 座位号或null, "extra": {{}}}}"""
    return [
        {
            "role": "system",
            "content": build_system_base(
                seat, role, state.day_number, phase_label, personality_block
            ),
        },
        {"role": "user", "content": user},
    ]


def build_belief_update_messages(
    state: GameState,
    seat: int,
    role: Role,
    own_actions_block: str,
    belief_json: str,
    personality_block: str,
) -> list[dict[str, str]]:
    """投票前单次信念链更新（仅合法信息）。"""
    phase_label = f"{state.phase.value}/{state.sub_phase.value if state.sub_phase else ''}"
    dialogue_block = format_public_memory_text(state)
    user = f"""【任务】根据己方行动历史、当前天公屏与现有信念，更新你对各座位的怀疑/信任/身份声明与待验证问题。
只能依据下方信息，禁止开天眼；座位号为 1～10 的整数。

【己方行动与技能历史】
{own_actions_block}

【当前天公屏（含历史天摘要）】
{dialogue_block}

【当前信念链 JSON】
{belief_json}

严格输出 JSON，不要 markdown：
{{"suspects": [座位号, ...], "trusted": [座位号, ...], "role_claims": {{"座位号": "seer_claim|witch_claim|..."}}, "open_questions": ["...", ...]}}
suspects/trusted 各最多 8 个；open_questions 最多 5 条。"""
    return [
        {
            "role": "system",
            "content": build_system_base(
                seat, role, state.day_number, phase_label, personality_block
            ),
        },
        {"role": "user", "content": user},
    ]


def _format_speech_turn_rules(seat: int, state_view: dict[str, Any]) -> str:
    """发言阶段顺序规则，防止 AI 对已过麦玩家要求再次表态。"""
    speech_ctx = state_view.get("speech_phase")
    if not speech_ctx:
        return ""

    already = speech_ctx.get("already_spoken_seats") or []
    already_str = "、".join(f"{s}号" for s in already) if already else "（尚无）"
    current = speech_ctx.get("current_speaker_seat")
    pending = speech_ctx.get("pending_speaker_seats") or []
    order = speech_ctx.get("speech_order") or []
    summary = speech_ctx.get("summary") or ""

    turn_hint = (
        "轮到你发言，请输出你的本轮发言。"
        if current == seat
        else f"当前轮到 {current} 号发言，你稍后轮次再发言。"
        if current is not None
        else "发言轮次已结束。"
    )

    return f"""【发言顺序规则（必须遵守）】
- 白天发言严格按顺序进行，每人本轮仅有一次发言机会；说完或过麦后不可再开口。
- 已发言/过麦的座位：{already_str}。不要对他们说「你怎么不表态」「请XX回应」「XX你说话」等期待其再次发言的话。
- 对已发言者只能评价、质疑或引用其**已说过的内容**，不能期待他们在本轮再次回应。
- 发言顺序：{' → '.join(str(s) for s in order) or '（未生成）'}
- {summary}
- 尚未发言：{'、'.join(f'{s}号' for s in pending) if pending else '（无）'}
- 你是 {seat} 号；{turn_hint}
"""


def build_speech_messages(
    state: GameState,
    seat: int,
    role: Role,
    state_view: dict[str, Any],
    strategy: StrategyEntry,
    belief_summary: str,
    personality_block: str,
    min_chars: int,
    max_chars: int,
) -> list[dict[str, str]]:
    phase_label = "白天发言"
    memory_block = format_memory_for_prompt(state, seat)
    speech_rules = _format_speech_turn_rules(seat, state_view)
    user = f"""【当前策略】{strategy.id} - {strategy.name}
{strategy.prompt_hint}

【信念摘要】
{belief_summary}
{speech_rules}
【合法信息】
{state_view}

【记忆】
{memory_block}

请生成一段白天公屏发言。
要求：简体中文，{min_chars}～{max_chars} 字，口语化，符合人格文风。
只输出发言正文，不要 JSON、不要编号列表标题。"""
    return [
        {
            "role": "system",
            "content": build_system_base(
                seat, role, state.day_number, phase_label, personality_block
            ),
        },
        {"role": "user", "content": user},
    ]

