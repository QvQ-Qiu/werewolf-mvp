"""角色技能与夜/日结算"""

import uuid
from datetime import datetime

from app.models.game import (
    CheckResult,
    GameState,
    NightActionBundle,
    Player,
    PublicLogEntry,
    Role,
    SubPhase,
)


def _log(
    state: GameState,
    content: str,
    log_type: str = "system",
    seat: int | None = None,
) -> None:
    phase_ref = f"{state.phase.value}_{state.day_number}"
    if state.sub_phase:
        phase_ref = f"{phase_ref}_{state.sub_phase.value}"
    state.public_log.append(
        PublicLogEntry(
            id=str(uuid.uuid4()),
            phase_ref=phase_ref,
            type=log_type,
            seat=seat,
            content=content,
            timestamp=datetime.utcnow(),
        )
    )


def kill_player(state: GameState, seat: int, reason: str = "") -> None:
    """使玩家死亡"""
    player = state.get_player(seat)
    if not player.is_alive:
        return
    player.is_alive = False
    state.alive_seats.discard(seat)
    msg = f"{seat}号玩家死亡"
    if reason:
        msg = f"{msg}（{reason}）"
    _log(state, msg, "death", seat)


def resolve_seer_check(state: GameState) -> None:
    """记录预言家验人结果（同一夜不重复写入）"""
    target = state.night_actions.seer_check_target
    if target is None:
        return
    if state.seer_checks and state.seer_checks[-1].night == state.day_number:
        return
    target_player = state.get_player(target)
    is_wolf = target_player.role == Role.WOLF
    state.seer_checks.append(
        CheckResult(night=state.day_number, target_seat=target, is_wolf=is_wolf)
    )


def seer_check_is_wolf(state: GameState, target_seat: int) -> bool:
    """根据服务端真相判断验人目标阵营"""
    return state.get_player(target_seat).role == Role.WOLF


def resolve_night_deaths(state: GameState) -> list[int]:
    """
    10 人屠边局（预女猎守）夜结算规则。

    夜晚行动子阶段顺序：狼人 → 预言家 → 女巫 → 守卫 → 结算。
    狼刀目标在离开守卫阶段、进入 NIGHT_RESOLVE 前由 resolve_wolf_kill 确定。

    夜结算生效顺序（与常见面杀规则一致）：
    1. 狼刀落在 wolf_kill_target（已出局则无视）
    2. 守卫守护可抵消狼刀
    3. 女巫解药可抵消狼刀（解药目标须为当夜狼刀目标，由 handler 校验）
    4. 同守同救：同一座位同时被狼刀、守护、解药 → 仍死于狼刀
    5. 女巫毒药独立结算，与狼刀无关；每夜最多一瓶药在行动阶段已约束

    返回本夜死亡列表（不含猎人开枪额外死亡）。
    """
    deaths: list[int] = []
    wolf_target = state.wolf_kill_target
    guard_target = state.night_actions.guard_protect_target
    heal_target = state.night_actions.witch_heal_target
    poison_target = state.night_actions.witch_poison_target

    if heal_target is not None and heal_target != wolf_target:
        heal_target = None

    dies_from_wolf = False
    if wolf_target is not None and state.get_player(wolf_target).is_alive:
        dies_from_wolf = True
        if guard_target == wolf_target:
            dies_from_wolf = False
        if heal_target == wolf_target:
            dies_from_wolf = False
        if (
            guard_target == wolf_target
            and heal_target == wolf_target
            and guard_target is not None
        ):
            dies_from_wolf = True

    if dies_from_wolf and wolf_target is not None:
        deaths.append(wolf_target)

    if poison_target is not None and poison_target not in deaths:
        if state.get_player(poison_target).is_alive:
            deaths.append(poison_target)

    state.last_night_deaths = deaths.copy()
    return deaths


def apply_night_deaths(
    state: GameState,
    deaths: list[int],
    reasons: dict[int, str] | None = None,
) -> None:
    """应用夜杀死亡；reasons 为座位→死因（如狼刀、毒杀）。"""
    for seat in deaths:
        kill_player(state, seat, (reasons or {}).get(seat, "夜间"))


def announce_night_deaths(state: GameState, deaths: list[int] | None = None) -> None:
    """
    天亮公布死讯。
    具体死亡座位已在 apply_night_deaths 写入公屏；此处仅补充「平安夜」汇总。
    deaths 优先于 state.last_night_deaths，避免与 DAY_ANNOUNCE 推进时序不一致。
    """
    died = deaths if deaths is not None else state.last_night_deaths
    if not died:
        _log(state, "昨晚是平安夜")


def exile_player(state: GameState, seat: int) -> None:
    """白天放逐"""
    kill_player(state, seat, "被放逐")
    state.last_exiled_seat = seat
    _log(state, f"{seat}号玩家被放逐出局", "death", seat)


def hunter_shoot(state: GameState, hunter_seat: int, target_seat: int | None) -> int | None:
    """
    猎人开枪。返回被射杀座位（若有）。
    被毒杀不能开枪（调用方需校验）。
    被放逐的猎人 is_alive=False 但仍可开枪。
    """
    hunter = state.get_player(hunter_seat)
    if not hunter.can_shoot:
        return None
    if target_seat is None:
        hunter.can_shoot = False
        return None

    target = state.get_player(target_seat)
    if not target.is_alive or target_seat == hunter_seat:
        return None

    hunter.can_shoot = False
    kill_player(state, target_seat, "被猎人射杀")
    return target_seat


def should_hunter_shoot_night(state: GameState, seat: int) -> bool:
    """夜杀后猎人是否可开枪（被毒杀不可开）"""
    player = state.get_player(seat)
    if player.role != Role.HUNTER or not player.can_shoot:
        return False
    if seat not in state.last_night_deaths:
        return False
    # 被毒杀不可开枪
    poison_target = state.night_actions.witch_poison_target
    if poison_target == seat and state.witch_state.poison_available is False:
        # 毒药已用于该目标
        if seat in state.last_night_deaths:
            # 若同时被毒，last_night_deaths 含该座位
            if state.night_actions.witch_poison_target == seat:
                return False
    # 简化：若死亡且被毒，不可开枪
    if state.night_actions.witch_poison_target == seat:
        return False
    return True


def should_hunter_shoot_exile(state: GameState, seat: int) -> bool:
    """放逐后猎人是否可开枪（已死亡但仍可开枪）"""
    player = state.get_player(seat)
    return (
        player.role == Role.HUNTER
        and player.can_shoot
        and state.last_exiled_seat == seat
        and state.night_actions.witch_poison_target != seat
    )


def reset_night_actions(state: GameState) -> None:
    """清空当夜行动"""
    state.night_actions = NightActionBundle()
    state.wolf_votes = []
    state.wolf_kill_target = None


def reset_day_actions(state: GameState) -> None:
    """清空本日行动"""
    state.speech_order = []
    state.current_speaker_index = 0
    state.speeches = {}
    state.day_votes = []
    state.last_exiled_seat = None


def build_speech_order(state: GameState) -> list[int]:
    """按座位号升序，存活玩家发言"""
    return sorted(state.alive_seats)


def find_role_seat(state: GameState, role: Role, alive_only: bool = True) -> int | None:
    for p in state.players:
        if p.role == role and (not alive_only or p.is_alive):
            return p.seat
    return None


def is_wolf(player: Player) -> bool:
    return player.role == Role.WOLF
