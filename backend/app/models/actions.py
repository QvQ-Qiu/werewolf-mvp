"""玩家行动类型"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ActionType(str, Enum):
    """行动类型枚举"""

    WOLF_NOMINATE = "wolf_nominate"
    SEER_CHECK = "seer_check"
    WITCH_HEAL = "witch_heal"
    WITCH_POISON = "witch_poison"
    GUARD_PROTECT = "guard_protect"
    PASS = "pass"
    VOTE = "vote"
    HUNTER_SHOOT = "hunter_shoot"
    SPEECH = "speech"


class Action(BaseModel):
    """统一行动对象（规则引擎入口）"""

    action_type: ActionType
    actor_seat: int
    target_seat: Optional[int] = None
    content: Optional[str] = None  # 发言内容
