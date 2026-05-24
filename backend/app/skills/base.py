"""Skills 插件系统 — 基础接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillContext:
    """Skill 执行上下文"""

    game_id: str | None = None
    seat: int | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Skill 执行结果"""

    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class BaseSkill(ABC):
    """Skill 基类 — 所有 Skill 需继承此类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill 名称（唯一标识）"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Skill 描述"""

    @abstractmethod
    async def execute(self, ctx: SkillContext) -> SkillResult:
        """执行 Skill"""

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def category(self) -> str:
        return "general"