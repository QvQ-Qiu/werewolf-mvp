"""OpenClaw 集成 — 将狼人杀后端暴露为 OpenClaw Tool / Skill"""

from __future__ import annotations

import json
from typing import Any

from app.skills.registry import skill_registry


# ── OpenClaw Tool 描述结构 ────────────────────────────────
# OpenClaw Tool 遵循以下格式：
#   { "name": str, "description": str, "parameters": dict }
# 其中 parameters 遵循 JSON Schema 格式。


def _build_openclaw_tools() -> list[dict[str, Any]]:
    """将已注册的 Skills 转为 OpenClaw Tool 列表"""
    tools = []
    for skill in skill_registry.list():
        parameters: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        tool = {
            "name": skill.name,
            "description": skill.description,
            "parameters": parameters,
        }
        tools.append(tool)
    return tools


def get_openclaw_config() -> dict[str, Any]:
    """生成 OpenClaw 配置片段，可直接嵌入 OpenClaw agent config"""
    tools = _build_openclaw_tools()
    return {
        "name": "werewolf",
        "version": "0.1.0",
        "description": "十人狼人杀 AI 对局服务",
        "tools": tools,
    }


# ── OpenClaw Agent 集成 ───────────────────────────────────


class OpenClawAdapter:
    """OpenClaw Agent Tool Adapter — 让 OpenClaw Agent 能调用狼人杀 Skill"""

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        """初始化：确保 Skills 已注册"""
        from app.skills.builtin import (
            CreateGameSkill,
            GetGameStateSkill,
            ListGamesSkill,
            SubmitVoteSkill,
            GetPublicLogSkill,
            HealthCheckSkill,
        )
        from app.skills.coze.skills import (
            CozeCheckInstalledSkill,
            CozeAuthStatusSkill,
            CozeAuthLoginSkill,
            CozeConfigListSkill,
            CozeConfigSetSkill,
            CozeOrganizationListSkill,
            CozeOrganizationUseSkill,
            CozeSpaceListSkill,
            CozeSpaceUseSkill,
            CozeGenerateImageSkill,
            CozeGenerateAudioSkill,
            CozeGenerateVideoSkill,
            CozeFileUploadSkill,
            CozeCodeProjectCreateSkill,
            CozeCodeMessageSendSkill,
            CozeCodeMessageStatusSkill,
            CozeCodeDeploySkill,
            CozeCodePreviewSkill,
            CozeRawCommandSkill,
        )
        from app.skills.llm.skills import (
            LLMChatSkill,
            LLMListModelsSkill,
        )

        builtins = [
            CreateGameSkill(),
            GetGameStateSkill(),
            ListGamesSkill(),
            SubmitVoteSkill(),
            GetPublicLogSkill(),
            HealthCheckSkill(),
            CozeCheckInstalledSkill(),
            CozeAuthStatusSkill(),
            CozeAuthLoginSkill(),
            CozeConfigListSkill(),
            CozeConfigSetSkill(),
            CozeOrganizationListSkill(),
            CozeOrganizationUseSkill(),
            CozeSpaceListSkill(),
            CozeSpaceUseSkill(),
            CozeGenerateImageSkill(),
            CozeGenerateAudioSkill(),
            CozeGenerateVideoSkill(),
            CozeFileUploadSkill(),
            CozeCodeProjectCreateSkill(),
            CozeCodeMessageSendSkill(),
            CozeCodeMessageStatusSkill(),
            CozeCodeDeploySkill(),
            CozeCodePreviewSkill(),
            CozeRawCommandSkill(),
            LLMChatSkill(),
            LLMListModelsSkill(),
        ]
        for s in builtins:
            skill_registry.register(s)
        self._initialized = True

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """获取 OpenClaw Tool 定义列表"""
        if not self._initialized:
            self.initialize()
        return _build_openclaw_tools()

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """执行 OpenClaw Tool 并返回 JSON 字符串"""
        from app.skills.base import SkillContext

        ctx = SkillContext(params=arguments)
        result = await skill_registry.execute(name, ctx)
        return json.dumps({"success": result.success, "message": result.message, "data": result.data}, ensure_ascii=False)


# 全局适配器实例
openclaw_adapter = OpenClawAdapter()