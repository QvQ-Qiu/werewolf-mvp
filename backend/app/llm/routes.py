"""LLM API 路由"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.llm.client import (
    COZE_INTEGRATION_BASE_URL,
    ChatMessage,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMClient,
    LLMConfig,
    LlmNotConfiguredError,
    get_qwen_client,
)
from app.llm.health import llm_is_ready

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health")
async def llm_health() -> dict:
    from app.llm.health import llm_status

    return llm_status()


@router.get("/models")
async def list_models(
    api_key: str = "",
    base_url: str = DEFAULT_BASE_URL,
):
    """获取可用模型列表（需提供 API Key）"""
    if not api_key:
        raise HTTPException(400, "缺少 api_key 参数")
    config = LLMConfig(api_key=api_key, base_url=base_url)
    client = LLMClient(config)
    try:
        models = client.list_models()
        return {"models": models, "count": len(models)}
    except Exception as e:
        raise HTTPException(500, f"获取模型列表失败: {e}")
    finally:
        client.close()


@router.post("/chat")
async def chat(body: dict):
    """LLM 对话（非流式，聚合 SSE 后返回）"""
    if not llm_is_ready():
        raise HTTPException(503, "LLM 未配置或不可达")

    messages = _parse_messages(body)
    client = get_qwen_client()
    try:
        result = await client.chat(
            messages,
            temperature=body.get("temperature", 0.7),
            max_tokens=body.get("max_tokens", 4096),
        )
        return {
            "content": result,
            "model": client._llm.config.model,
        }
    except Exception as e:
        raise HTTPException(500, f"LLM 调用失败: {e}") from e
    finally:
        client.close()


@router.post("/chat/stream")
async def chat_stream(body: dict):
    """LLM 流式对话 — SSE：`data: {"delta":"..."}`，结束 `data: [DONE]`"""
    if not llm_is_ready():
        raise HTTPException(503, "LLM 未配置或不可达")

    messages = _parse_messages(body)
    client = get_qwen_client()

    async def event_generator():
        try:
            async for piece in client.chat_stream_messages(
                messages,
                temperature=body.get("temperature", 0.7),
                max_tokens=body.get("max_tokens", 4096),
            ):
                yield f"data: {json.dumps({'delta': piece}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            client.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _parse_messages(body: dict) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    system_prompt = body.get("system_prompt", "")
    if system_prompt:
        out.append({"role": "system", "content": system_prompt})
    raw_msgs = body.get("messages", [])
    if raw_msgs:
        for m in raw_msgs:
            out.append({"role": m["role"], "content": m["content"]})
    elif body.get("prompt"):
        out.append({"role": "user", "content": body["prompt"]})
    if not out:
        raise HTTPException(400, "缺少 prompt 或 messages")
    return out


# 保留带显式 api_key 的调试接口（可选）
@router.post("/chat/raw")
async def chat_raw(body: dict):
    api_key = body.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "缺少 api_key")

    config = LLMConfig(
        api_key=api_key,
        base_url=body.get("base_url", COZE_INTEGRATION_BASE_URL),
        model=body.get("model", DEFAULT_MODEL),
        max_tokens=body.get("max_tokens", 4096),
        temperature=body.get("temperature", 0.7),
        top_p=body.get("top_p", 0.9),
    )
    client = LLMClient(config)
    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in _parse_messages(body)]

    try:
        result = client.chat(messages)
        return {
            "content": result.content,
            "model": result.model,
            "usage": result.usage,
            "finish_reason": result.finish_reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"LLM 调用失败: {e}") from e
    finally:
        client.close()
