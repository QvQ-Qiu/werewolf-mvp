"""LLM 连通性探测（启动时与 /health 复用）"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_llm_ready: bool | None = None
_llm_last_error: str | None = None


def probe_llm(force: bool = False) -> bool:
    """探测配置的 LLM 是否可正常调用。"""
    global _llm_ready, _llm_last_error

    if not force and _llm_ready is not None:
        return _llm_ready

    if not settings.has_llm_configured:
        _llm_ready = False
        _llm_last_error = "未配置 LLM（COZE_INTEGRATION_API_KEY / LLM_BASE_URL 等）"
        return False

    from app.llm.client import ChatMessage, LlmNotConfiguredError, get_qwen_client

    try:
        client = get_qwen_client()
        client._llm.chat(
            [ChatMessage(role="user", content="ping")],
            max_tokens=8,
        )
        _llm_ready = True
        _llm_last_error = None
        logger.info("LLM 连通性检查通过 model=%s", client._llm.config.model)
        return True
    except LlmNotConfiguredError as exc:
        _llm_ready = False
        _llm_last_error = str(exc)
    except Exception as exc:
        _llm_ready = False
        _llm_last_error = str(exc)
        logger.error("LLM 连通性检查失败: %s", exc)

    return False


def llm_is_ready() -> bool:
    if _llm_ready is None:
        probe_llm()
    return bool(_llm_ready)


def reset_llm_probe_cache() -> None:
    global _llm_ready, _llm_last_error
    _llm_ready = None
    _llm_last_error = None


def llm_status() -> dict[str, Any]:
    probe_llm()
    provider = "none"
    model = settings.qwen_model
    if settings.llm_base_url.strip():
        provider = "openai_compatible"
        model = settings.llm_model
    elif settings.coze_integration_api_key:
        provider = "coze_integration"
        model = settings.coze_integration_model
    elif settings.ark_api_key:
        provider = "ark"
        model = settings.ark_model
    elif settings.dashscope_api_key or settings.qwen_api_key:
        provider = "dashscope"
    elif settings.openai_api_key:
        provider = "openai"
        model = settings.llm_model

    return {
        "configured": settings.has_llm_configured,
        "reachable": llm_is_ready(),
        "provider": provider,
        "model": model,
        "error": _llm_last_error,
    }
