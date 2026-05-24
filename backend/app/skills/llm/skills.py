"""LLM Skills — 调用豆包/OpenAI 兼容大模型"""

from __future__ import annotations

from app.llm.client import LLMConfig, LLMClient, ChatMessage
from app.skills.base import BaseSkill, SkillContext, SkillResult


class LLMChatSkill(BaseSkill):
    """LLM 对话 — 调用豆包/OpenAI 兼容大模型"""

    name = "llm_chat"
    description = "调用豆包（Doubao）/ OpenAI 兼容大模型进行对话，返回 AI 回复"
    category = "llm"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        prompt = ctx.params.get("prompt", "")
        system_prompt = ctx.params.get("system_prompt", "")
        model = ctx.params.get("model", "doubao-seed-2-0-mini-260215")
        api_key = ctx.params.get("api_key", "")
        base_url = ctx.params.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")

        if not api_key:
            return SkillResult(success=False, message="缺少 api_key 参数")
        if not prompt:
            return SkillResult(success=False, message="缺少 prompt 参数")

        config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        client = LLMClient(config)
        try:
            messages: list[ChatMessage] = []
            if system_prompt:
                messages.append(ChatMessage(role="system", content=system_prompt))
            messages.append(ChatMessage(role="user", content=prompt))
            result = client.chat(messages)
            return SkillResult(
                success=True,
                data={
                    "content": result.content,
                    "model": result.model,
                    "usage": result.usage,
                    "finish_reason": result.finish_reason,
                },
            )
        except Exception as e:
            return SkillResult(success=False, message=str(e))
        finally:
            client.close()


class LLMListModelsSkill(BaseSkill):
    """获取模型列表"""

    name = "llm_list_models"
    description = "获取 LLM 服务商支持的可用模型列表"
    category = "llm"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        api_key = ctx.params.get("api_key", "")
        base_url = ctx.params.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")
        if not api_key:
            return SkillResult(success=False, message="缺少 api_key 参数")
        config = LLMConfig(api_key=api_key, base_url=base_url)
        client = LLMClient(config)
        try:
            models = client.list_models()
            return SkillResult(
                success=True,
                data={"models": models, "count": len(models)},
            )
        except Exception as e:
            return SkillResult(success=False, message=str(e))
        finally:
            client.close()