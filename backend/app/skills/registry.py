"""Skills 注册表 — 管理所有 Skill 的注册、发现与调用"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Any

from app.skills.base import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class SkillRegistry:
    """全局 Skill 注册表"""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """注册一个 Skill 实例"""
        if skill.name in self._skills:
            logger.warning("Skill '%s' 已注册，将被覆盖", skill.name)
        self._skills[skill.name] = skill
        logger.info("Skill 已注册: %s v%s [%s]", skill.name, skill.version, skill.category)

    def unregister(self, name: str) -> None:
        """注销 Skill"""
        self._skills.pop(name, None)

    def get(self, name: str) -> BaseSkill | None:
        """按名称获取 Skill"""
        return self._skills.get(name)

    def list(self, category: str | None = None) -> list[BaseSkill]:
        """列出所有（或指定分类的）Skill"""
        if category is None:
            return list(self._skills.values())
        return [s for s in self._skills.values() if s.category == category]

    def list_skills_info(self) -> list[dict[str, Any]]:
        """返回所有 Skill 的元信息"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "category": s.category,
            }
            for s in self._skills.values()
        ]

    async def execute(self, name: str, ctx: SkillContext | None = None) -> SkillResult:
        """执行指定名称的 Skill"""
        skill = self.get(name)
        if skill is None:
            return SkillResult(success=False, message=f"Skill '{name}' 未找到")
        return await skill.execute(ctx or SkillContext())

    def discover(self, package: str = "app.skills.builtin") -> int:
        """自动发现并注册指定包下的所有 Skill 子类"""
        count = 0
        try:
            pkg = importlib.import_module(package)
            for importer, modname, ispkg in pkgutil.walk_packages(
                pkg.__path__, prefix=f"{package}.",
            ):
                try:
                    mod = importlib.import_module(modname)
                    for name, obj in inspect.getmembers(mod, inspect.isclass):
                        if (
                            issubclass(obj, BaseSkill)
                            and obj is not BaseSkill
                            and not getattr(obj, "__abstractmethods__", None)
                        ):
                            instance = obj()
                            self.register(instance)
                            count += 1
                except Exception as e:
                    logger.warning("加载 Skill 模块 %s 失败: %s", modname, e)
        except ImportError:
            logger.info("Skill 包 %s 不存在，跳过自动发现", package)
        return count


# 全局单例
skill_registry = SkillRegistry()