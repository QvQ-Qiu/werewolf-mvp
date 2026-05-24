"""规则引擎入口：校验行动、驱动状态机"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.game.dealing import setup_game
from app.game.roles import (
    _log,
    find_role_seat,
    hunter_shoot,
    should_hunter_shoot_exile,
    should_hunter_shoot_night,
)
from app.game.state_machine import advance_sub_phase
from app.game.win_condition import check_winner
from app.models.actions import Action, ActionType
from app.models.game import (
    DayVoteRecord,
    GameState,
    GameStatus,
    Phase,
    PublicLogEntry,
    Role,
    SubPhase,
)


@dataclass
class ApplyResult:
    ok: bool
    message: str
    sub_phase_complete: bool = False


class RuleEngine:
    """规则引擎：唯一有权修改 GameState 的模块"""

    def __init__(self, state: GameState, rng: random.Random | None = None) -> None:
        self.state = state
        self.rng = rng or random.Random(state.seed)

    def setup(self, player_name: str, seed: int | None = None) -> tuple[int, Role]:
        """发牌并进入首夜"""
        return setup_game(self.state, player_name, seed)

    def apply_action(self, action: Action) -> ApplyResult:
        """校验并应用行动"""
        if self.state.phase == Phase.GAME_OVER:
            return ApplyResult(False, "对局已结束")

        handler = {
            ActionType.WOLF_NOMINATE: self._handle_wolf_nominate,
            ActionType.SEER_CHECK: self._handle_seer_check,
            ActionType.WITCH_HEAL: self._handle_witch_heal,
            ActionType.WITCH_POISON: self._handle_witch_poison,
            ActionType.GUARD_PROTECT: self._handle_guard_protect,
            ActionType.PASS: self._handle_pass,
            ActionType.VOTE: self._handle_vote,
            ActionType.HUNTER_SHOOT: self._handle_hunter_shoot,
            ActionType.SPEECH: self._handle_speech,
        }.get(action.action_type)

        if handler is None:
            return ApplyResult(False, f"未知行动类型 {action.action_type}")

        return handler(action)

    def advance_phase(self) -> str:
        """推进子阶段（当当前子阶段已完成时调用）"""
        return advance_sub_phase(self.state, self.rng)

    def is_sub_phase_complete(self) -> bool:
        """当前子阶段是否已收集足够行动"""
        sub = self.state.sub_phase
        s = self.state

        if sub == SubPhase.NIGHT_WOLF:
            wolves = s.alive_wolves()
            noms = s.night_actions.wolf_nominations
            return all(w.seat in noms for w in wolves)

        if sub == SubPhase.NIGHT_SEER:
            seer_seat = find_role_seat(s, Role.SEER)
            if seer_seat is None or seer_seat not in s.alive_seats:
                return True
            return s.night_actions.seer_check_target is not None

        if sub == SubPhase.NIGHT_WITCH:
            witch_seat = find_role_seat(s, Role.WITCH)
            if witch_seat is None or witch_seat not in s.alive_seats:
                return True
            return s.night_actions.witch_done

        if sub == SubPhase.NIGHT_GUARD:
            guard_seat = find_role_seat(s, Role.GUARD)
            if guard_seat is None or guard_seat not in s.alive_seats:
                return True
            return s.night_actions.guard_done

        if sub == SubPhase.NIGHT_RESOLVE:
            return True

        if sub == SubPhase.DAY_ANNOUNCE:
            return True

        if sub == SubPhase.DAY_SPEECH:
            if not s.speech_order:
                return True
            return s.current_speaker_index >= len(s.speech_order)

        if sub == SubPhase.DAY_VOTE:
            alive = sorted(s.alive_seats)
            voted = {v.voter_seat for v in s.day_votes}
            return all(seat in voted for seat in alive)

        if sub == SubPhase.DAY_RESOLVE:
            return True

        if sub == SubPhase.HUNTER_SHOOT:
            return s.pending_hunter_seat is None

        return False

    def check_winner(self):
        return check_winner(self.state)

    def auto_advance_until_blocking(self, max_steps: int = 50) -> list[str]:
        """自动推进直至需要行动或结束"""
        messages: list[str] = []
        for _ in range(max_steps):
            if self.state.phase == Phase.GAME_OVER:
                break

            # 自动跳过无行动者的子阶段
            if self._should_auto_skip_sub_phase():
                msg = self.advance_phase()
                messages.append(msg)
                continue

            if self.is_sub_phase_complete():
                msg = self.advance_phase()
                messages.append(msg)
                continue

            break
        return messages

    def _should_auto_skip_sub_phase(self) -> bool:
        sub = self.state.sub_phase
        s = self.state
        if sub == SubPhase.NIGHT_SEER:
            seer = find_role_seat(s, Role.SEER)
            return seer is None or seer not in s.alive_seats
        if sub == SubPhase.NIGHT_WITCH:
            witch = find_role_seat(s, Role.WITCH)
            return witch is None or witch not in s.alive_seats
        if sub == SubPhase.NIGHT_GUARD:
            guard = find_role_seat(s, Role.GUARD)
            return guard is None or guard not in s.alive_seats
        if sub == SubPhase.DAY_ANNOUNCE:
            return True
        if sub == SubPhase.NIGHT_RESOLVE:
            return True
        if sub == SubPhase.DAY_RESOLVE:
            return True
        if sub == SubPhase.HUNTER_SHOOT:
            return s.pending_hunter_seat is None
        return False

    # --- 行动处理器 ---

    def _handle_wolf_nominate(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.NIGHT_WOLF:
            return ApplyResult(False, "当前不是狼刀阶段")
        actor = self._require_alive_actor(action, Role.WOLF)
        if actor is None:
            return ApplyResult(False, "行动者不合法")
        if action.target_seat is None or action.target_seat not in self.state.alive_seats:
            return ApplyResult(False, "刀口目标无效")
        self.state.night_actions.wolf_nominations[action.actor_seat] = action.target_seat
        complete = self.is_sub_phase_complete()
        return ApplyResult(True, "狼刀提名成功", sub_phase_complete=complete)

    def _handle_seer_check(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.NIGHT_SEER:
            return ApplyResult(False, "当前不是预言家阶段")
        if action.actor_seat != find_role_seat(self.state, Role.SEER):
            return ApplyResult(False, "仅预言家可验人")
        if action.actor_seat not in self.state.alive_seats:
            return ApplyResult(False, "预言家已死亡")
        if action.target_seat is None or action.target_seat not in self.state.alive_seats:
            return ApplyResult(False, "验人目标无效")
        self.state.night_actions.seer_check_target = action.target_seat
        return ApplyResult(True, "验人成功", sub_phase_complete=True)

    def _witch_used_potion_tonight(self) -> bool:
        na = self.state.night_actions
        return na.witch_heal_target is not None or na.witch_poison_target is not None

    def _handle_witch_heal(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.NIGHT_WITCH:
            return ApplyResult(False, "当前不是女巫阶段")
        witch_seat = find_role_seat(self.state, Role.WITCH)
        if action.actor_seat != witch_seat or witch_seat not in self.state.alive_seats:
            return ApplyResult(False, "仅存活女巫可行动")
        if self._witch_used_potion_tonight():
            return ApplyResult(False, "每夜最多使用一瓶药水")
        if not self.state.witch_state.heal_available:
            return ApplyResult(False, "解药已用完")
        if action.target_seat is None:
            return ApplyResult(False, "请指定救人目标")
        # 首夜可自救；解药目标必须是当夜狼刀目标（狼刀在 resolve 时才最终确定，此处用提名推算）
        # 女巫阶段在 guard 之前，狼刀已通过 AI 票确定逻辑在 resolve 前——按规则女巫在 guard 前行动
        # 实际上顺序是狼→预→女→守，狼刀目标在 wolf 阶段结束即可算出
        from app.game.voting import resolve_wolf_kill

        if self.state.wolf_kill_target is None:
            self.state.wolf_kill_target = resolve_wolf_kill(self.state, self.rng)
        wolf_target = self.state.wolf_kill_target
        if action.target_seat != wolf_target:
            return ApplyResult(False, "解药只能救当夜狼刀目标")
        if action.target_seat not in self.state.alive_seats:
            return ApplyResult(False, "目标无效")
        self.state.night_actions.witch_heal_target = action.target_seat
        self.state.witch_state.heal_available = False
        self.state.night_actions.witch_done = True
        return ApplyResult(True, "女巫救人", sub_phase_complete=True)

    def _handle_witch_poison(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.NIGHT_WITCH:
            return ApplyResult(False, "当前不是女巫阶段")
        witch_seat = find_role_seat(self.state, Role.WITCH)
        if action.actor_seat != witch_seat or witch_seat not in self.state.alive_seats:
            return ApplyResult(False, "仅存活女巫可行动")
        if self._witch_used_potion_tonight():
            return ApplyResult(False, "每夜最多使用一瓶药水")
        if not self.state.witch_state.poison_available:
            return ApplyResult(False, "毒药已用完")
        if action.target_seat is None or action.target_seat not in self.state.alive_seats:
            return ApplyResult(False, "毒杀目标无效")
        self.state.night_actions.witch_poison_target = action.target_seat
        self.state.witch_state.poison_available = False
        self.state.night_actions.witch_done = True
        return ApplyResult(True, "女巫毒人", sub_phase_complete=True)

    def _handle_guard_protect(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.NIGHT_GUARD:
            return ApplyResult(False, "当前不是守卫阶段")
        guard_seat = find_role_seat(self.state, Role.GUARD)
        if action.actor_seat != guard_seat or guard_seat not in self.state.alive_seats:
            return ApplyResult(False, "仅存活守卫可行动")
        if action.target_seat is None or action.target_seat not in self.state.alive_seats:
            return ApplyResult(False, "守护目标无效")
        if (
            self.state.guard_last_target is not None
            and action.target_seat == self.state.guard_last_target
        ):
            return ApplyResult(False, "不能连续两夜守护同一人")
        self.state.night_actions.guard_protect_target = action.target_seat
        self.state.guard_last_target = action.target_seat
        self.state.night_actions.guard_done = True
        return ApplyResult(True, "守卫守护", sub_phase_complete=True)

    def _handle_pass(self, action: Action) -> ApplyResult:
        sub = self.state.sub_phase
        if sub == SubPhase.NIGHT_WITCH:
            witch_seat = find_role_seat(self.state, Role.WITCH)
            if action.actor_seat != witch_seat:
                return ApplyResult(False, "仅女巫可结束行动")
            self.state.night_actions.witch_done = True
            return ApplyResult(True, "女巫跳过", sub_phase_complete=True)
        if sub == SubPhase.NIGHT_GUARD:
            guard_seat = find_role_seat(self.state, Role.GUARD)
            if action.actor_seat != guard_seat:
                return ApplyResult(False, "仅守卫可跳过")
            self.state.night_actions.guard_done = True
            return ApplyResult(True, "守卫跳过", sub_phase_complete=True)
        if sub == SubPhase.HUNTER_SHOOT:
            if action.actor_seat != self.state.pending_hunter_seat:
                return ApplyResult(False, "非待开枪猎人")
            self.state.pending_hunter_seat = None
            self.state.get_player(action.actor_seat).can_shoot = False
            return ApplyResult(True, "猎人不开枪", sub_phase_complete=True)
        if sub == SubPhase.DAY_VOTE:
            return self._handle_vote(
                Action(action_type=ActionType.VOTE, actor_seat=action.actor_seat, target_seat=None)
            )
        return ApplyResult(False, "当前阶段不支持 PASS")

    def _handle_vote(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.DAY_VOTE:
            return ApplyResult(False, "当前不是投票阶段")
        if action.actor_seat not in self.state.alive_seats:
            return ApplyResult(False, "仅存活玩家可投票")
        if any(v.voter_seat == action.actor_seat for v in self.state.day_votes):
            return ApplyResult(False, "已投过票")
        if action.target_seat is not None and action.target_seat not in self.state.alive_seats:
            return ApplyResult(False, "投票目标无效")
        self.state.day_votes.append(
            DayVoteRecord(voter_seat=action.actor_seat, target_seat=action.target_seat)
        )
        complete = self.is_sub_phase_complete()
        return ApplyResult(True, "投票成功", sub_phase_complete=complete)

    def _handle_hunter_shoot(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.HUNTER_SHOOT:
            return ApplyResult(False, "当前不是猎人开枪阶段")
        hunter_seat = self.state.pending_hunter_seat
        if hunter_seat is None or action.actor_seat != hunter_seat:
            return ApplyResult(False, "非待开枪猎人")
        player = self.state.get_player(hunter_seat)
        if not player.can_shoot:
            return ApplyResult(False, "猎人已不可开枪")
        # 校验是否允许开枪
        if not (
            should_hunter_shoot_night(self.state, hunter_seat)
            or should_hunter_shoot_exile(self.state, hunter_seat)
        ):
            return ApplyResult(False, "当前情况猎人不能开枪")

        target = action.target_seat
        if target is not None and target not in self.state.alive_seats:
            return ApplyResult(False, "目标无效")
        shot = hunter_shoot(self.state, hunter_seat, target)
        self.state.pending_hunter_seat = None
        detail = f"射杀 {shot} 号" if shot else "未射杀"
        return ApplyResult(True, f"猎人开枪，{detail}", sub_phase_complete=True)

    def _handle_speech(self, action: Action) -> ApplyResult:
        if self.state.sub_phase != SubPhase.DAY_SPEECH:
            return ApplyResult(False, "当前不是发言阶段")
        if not self.state.speech_order:
            return ApplyResult(False, "发言顺序未生成")
        if self.state.current_speaker_index >= len(self.state.speech_order):
            return ApplyResult(False, "发言已结束")
        expected = self.state.speech_order[self.state.current_speaker_index]
        if action.actor_seat != expected:
            return ApplyResult(False, f"当前应 {expected} 号发言")
        if action.actor_seat not in self.state.alive_seats:
            return ApplyResult(False, "发言者已死亡")
        content = action.content or ""
        self.state.speeches[action.actor_seat] = content
        self.state.public_log.append(
            PublicLogEntry(
                id=str(uuid.uuid4()),
                phase_ref=f"day_{self.state.day_number}_speech",
                type="speech",
                seat=action.actor_seat,
                content=content,
                timestamp=datetime.utcnow(),
            )
        )
        self.state.current_speaker_index += 1
        complete = self.is_sub_phase_complete()
        return ApplyResult(True, "发言记录", sub_phase_complete=complete)

    def _require_alive_actor(self, action: Action, role: Role) -> Role | None:
        player = self.state.get_player(action.actor_seat)
        if not player.is_alive or player.role != role:
            return None
        return player.role


def create_engine(state: GameState, seed: int | None = None) -> RuleEngine:
    rng = random.Random(seed if seed is not None else state.seed)
    return RuleEngine(state, rng)
