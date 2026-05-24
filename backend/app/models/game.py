"""游戏核心数据模型"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """角色"""

    WOLF = "wolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    GUARD = "guard"
    VILLAGER = "villager"


class Phase(str, Enum):
    """主阶段"""

    SETUP = "setup"
    NIGHT = "night"
    DAY = "day"
    GAME_OVER = "game_over"


class SubPhase(str, Enum):
    """子阶段"""

    NIGHT_WOLF = "night_wolf"
    NIGHT_SEER = "night_seer"
    NIGHT_WITCH = "night_witch"
    NIGHT_GUARD = "night_guard"
    NIGHT_RESOLVE = "night_resolve"
    DAY_ANNOUNCE = "day_announce"
    DAY_SPEECH = "day_speech"
    DAY_VOTE = "day_vote"
    DAY_RESOLVE = "day_resolve"
    HUNTER_SHOOT = "hunter_shoot"


class Faction(str, Enum):
    """阵营"""

    WOLF = "wolf"
    VILLAGE = "village"


class GameStatus(str, Enum):
    """对局状态"""

    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


# 神职角色集合（屠边判定用）
GOD_ROLES = {Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD}


class WitchState(BaseModel):
    """女巫药水状态"""

    heal_available: bool = True
    poison_available: bool = True


class WolfVote(BaseModel):
    """狼刀提名记录"""

    nominator_seat: int
    target_seat: int
    is_effective: bool  # 玩家狼提名不计入有效票


class CheckResult(BaseModel):
    """预言家验人结果（仅服务端全知）"""

    night: int
    target_seat: int
    is_wolf: bool


class NightActionBundle(BaseModel):
    """当夜收集的原始行动"""

    wolf_nominations: dict[int, int] = Field(default_factory=dict)  # 狼座位 -> 刀口
    seer_check_target: Optional[int] = None
    witch_heal_target: Optional[int] = None
    witch_poison_target: Optional[int] = None
    guard_protect_target: Optional[int] = None
    witch_done: bool = False
    guard_done: bool = False


class DayVoteRecord(BaseModel):
    """白天投票记录"""

    voter_seat: int
    target_seat: Optional[int] = None  # None 表示弃票


class Player(BaseModel):
    """玩家"""

    seat: int = Field(ge=1, le=10)
    name: str
    is_human: bool = False
    role: Optional[Role] = None
    is_alive: bool = True
    persona_id: Optional[str] = None
    can_shoot: bool = True  # 猎人是否可开枪


class PublicLogEntry(BaseModel):
    """公屏日志"""

    id: str
    phase_ref: str = ""
    type: str  # system | speech | vote | death | skill_reveal
    seat: Optional[int] = None
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StrategyUsageRecord(BaseModel):
    """策略使用记录"""

    strategy_id: str
    phase_ref: str
    reason: str = ""


class PublicClaim(BaseModel):
    """公开身份声明 / 报验（真假分开）"""

    day: int
    claim_type: str  # role_claim | seer_check | alignment
    content: str
    is_truthful: bool = True


class BeliefState(BaseModel):
    """逻辑链 / 信念（后台，不对存活玩家展示）"""

    suspects: list[int] = Field(default_factory=list)
    trusted: list[int] = Field(default_factory=list)
    role_claims: dict[str, str] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)


class PlayerMemory(BaseModel):
    """单玩家记忆（策略史、承诺、票型）"""

    seat: int
    strategy_history: list[StrategyUsageRecord] = Field(default_factory=list)
    public_claims: list[PublicClaim] = Field(default_factory=list)
    vote_history: list[dict[str, Any]] = Field(default_factory=list)
    kill_history: list[dict[str, Any]] = Field(default_factory=list)
    seer_checks_truth: list[dict[str, Any]] = Field(default_factory=list)


class PrivateMessage(BaseModel):
    """私域消息"""

    id: str
    sender_seat: Optional[int] = None
    receiver_seat: int
    channel: str  # seer_result | system
    content: str
    phase_ref: str = ""
    visible_to: list[int] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LlmTrace(BaseModel):
    """LLM 调用追溯（复盘用）"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_seat: int
    step: str  # select_strategy | decide_action | generate_speech
    strategy_id: Optional[str] = None
    phase_ref: str = ""
    prompt_summary: str = ""
    response_summary: str = ""
    messages_full: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BeliefStateDto(BaseModel):
    """信念状态（复盘披露）"""

    seat: int
    suspects: list[int] = Field(default_factory=list)
    trusted: list[int] = Field(default_factory=list)
    role_claims: dict[str, str] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)


class PlayerMemoryDto(BaseModel):
    """玩家记忆摘要（复盘）"""

    seat: int
    strategy_history: list[dict[str, Any]] = Field(default_factory=list)
    public_claims: list[dict[str, Any]] = Field(default_factory=list)
    vote_history: list[dict[str, Any]] = Field(default_factory=list)


class GameState(BaseModel):
    """对局状态（规则引擎真相源）"""

    game_id: str
    seed: int = 0
    status: GameStatus = GameStatus.WAITING
    phase: Phase = Phase.SETUP
    sub_phase: Optional[SubPhase] = None
    day_number: int = 0
    players: list[Player] = Field(default_factory=list)
    alive_seats: set[int] = Field(default_factory=set)
    night_actions: NightActionBundle = Field(default_factory=NightActionBundle)
    witch_state: WitchState = Field(default_factory=WitchState)
    guard_last_target: Optional[int] = None
    wolf_votes: list[WolfVote] = Field(default_factory=list)
    wolf_kill_target: Optional[int] = None  # 当夜狼刀最终目标
    seer_checks: list[CheckResult] = Field(default_factory=list)
    speech_order: list[int] = Field(default_factory=list)
    current_speaker_index: int = 0
    speeches: dict[int, str] = Field(default_factory=dict)  # 本日发言
    day_votes: list[DayVoteRecord] = Field(default_factory=list)
    pending_hunter_seat: Optional[int] = None  # 待开枪的猎人座位
    last_night_deaths: list[int] = Field(default_factory=list)
    last_exiled_seat: Optional[int] = None
    public_log: list[PublicLogEntry] = Field(default_factory=list)
    # 公共记忆压缩：已完成天数的摘要 + 当前天完整公屏
    round_memory_summaries: list[str] = Field(default_factory=list)
    current_round_log_start_index: int = 0
    winner: Optional[Faction] = None
    # Phase 3：AI 认知与复盘追溯
    personality_library_id: str = "default"
    strategy_library_id: str = "default"
    personality_by_seat: dict[int, dict[str, Any]] = Field(default_factory=dict)
    player_memories: dict[int, PlayerMemory] = Field(default_factory=dict)
    belief_by_seat: dict[int, BeliefState] = Field(default_factory=dict)
    private_messages: list[PrivateMessage] = Field(default_factory=list)
    llm_traces: list[LlmTrace] = Field(default_factory=list)

    def get_player(self, seat: int) -> Player:
        for p in self.players:
            if p.seat == seat:
                return p
        raise ValueError(f"座位 {seat} 不存在")

    def alive_wolves(self) -> list[Player]:
        return [p for p in self.players if p.is_alive and p.role == Role.WOLF]

    def alive_gods(self) -> list[Player]:
        return [p for p in self.players if p.is_alive and p.role in GOD_ROLES]


# --- API 请求/响应 ---


class CreateGameRequest(BaseModel):
    player_name: str
    seed: Optional[int] = None
    personality_library_id: Optional[str] = None
    strategy_library_id: Optional[str] = None


class CreateGameResponse(BaseModel):
    game_id: str
    ws_url: str
    player_token: str
    human_seat: int
    human_role: Role


class PlayerPublicInfo(BaseModel):
    """公开玩家信息（不含身份）"""

    seat: int
    name: str
    is_alive: bool
    is_human: bool


class GameSummary(BaseModel):
    game_id: str
    status: GameStatus
    phase: Phase
    sub_phase: Optional[SubPhase] = None
    day_number: int
    winner: Optional[Faction] = None
    players: list[PlayerPublicInfo] = Field(default_factory=list)
    public_log: list[PublicLogEntry] = Field(default_factory=list)


class ReplayPlayerInfo(BaseModel):
    """复盘玩家（局后披露身份）"""

    seat: int
    name: str
    role: Role
    is_alive: bool
    is_human: bool
    persona_id: Optional[str] = None
    personality_name: Optional[str] = None


class GameListItem(BaseModel):
    """对局列表项"""

    game_id: str
    status: GameStatus
    phase: Phase
    day_number: int
    human_player_name: str
    winner: Optional[Faction] = None
    created_at: float = 0.0


class GameReplayResponse(BaseModel):
    """局后复盘（消费 state 内已有 public_log / llm_traces / private_messages）"""

    game_id: str
    status: GameStatus
    phase: Phase
    day_number: int
    winner: Optional[Faction] = None
    human_seat: int
    players: list[ReplayPlayerInfo] = Field(default_factory=list)
    public_log: list[PublicLogEntry] = Field(default_factory=list)
    llm_traces: list[LlmTrace] = Field(default_factory=list)
    private_messages: list[PrivateMessage] = Field(default_factory=list)
    belief_by_seat: list[BeliefStateDto] = Field(default_factory=list)
    player_memories: list[PlayerMemoryDto] = Field(default_factory=list)


class SubmitActionRequest(BaseModel):
    action_type: str
    actor_seat: int
    target_seat: Optional[int] = None
    content: Optional[str] = None


class SubmitActionResponse(BaseModel):
    ok: bool
    message: str
    sub_phase_complete: bool = False
    phase: Phase
    sub_phase: Optional[SubPhase] = None
    winner: Optional[Faction] = None


class AdvancePhaseResponse(BaseModel):
    ok: bool
    message: str
    phase: Phase
    sub_phase: Optional[SubPhase] = None
    winner: Optional[Faction] = None
