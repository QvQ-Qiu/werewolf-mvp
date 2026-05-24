"""LLM 客户端 — 火山方舟/OpenAI 兼容接口封装"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── 异常 ──────────────────────────────────────────────


class LlmNotConfiguredError(Exception):
    """LLM 未配置"""


# ── 默认配置 ──────────────────────────────────────────

COZE_INTEGRATION_BASE_URL = "https://integration.coze.cn/api/v3"
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed-2-0-mini-260215"  # Doubao Seed 2.0 Mini Model ID
DEFAULT_TIMEOUT = 60


def _aggregate_sse_response(body: str, default_model: str) -> ChatCompletionResult:
    """Coze Integration 等端点可能在 stream=false 时仍返回 SSE。"""
    content_parts: list[str] = []
    model = default_model
    usage: dict[str, int] = {}
    finish_reason = ""

    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if not chunk or chunk == "[DONE]":
            continue
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        model = data.get("model", model)
        if data.get("usage"):
            usage = data["usage"]
        choices = data.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        finish_reason = choice.get("finish_reason") or finish_reason
        delta = choice.get("delta") or {}
        msg = choice.get("message") or {}
        piece = delta.get("content") or msg.get("content") or ""
        if piece:
            content_parts.append(piece)

    return ChatCompletionResult(
        content="".join(content_parts),
        model=model,
        usage=usage,
        finish_reason=finish_reason,
        raw={"sse": True},
    )


# ── 数据结构 ──────────────────────────────────────────


@dataclass
class LLMConfig:
    """LLM 客户端配置"""

    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: int = DEFAULT_TIMEOUT
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9


@dataclass
class ChatMessage:
    """对话消息"""

    role: str  # system | user | assistant
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatCompletionResult:
    """对话完成结果"""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


# ── 客户端 ────────────────────────────────────────────


class LLMClient:
    """OpenAI 兼容 LLM 客户端

    支持火山方舟 Ark API 以及其他 OpenAI 兼容接口。
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self._client = httpx.Client(timeout=self.config.timeout)
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    @property
    def _chat_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/chat/completions"

    @property
    def _models_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/models"

    def _build_payload(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": stream,
        }
        # 允许显式覆盖
        for key in ("model",):
            if key in kwargs:
                payload[key] = kwargs[key]
        return {k: v for k, v in payload.items() if v is not None}

    def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> ChatCompletionResult:
        """非流式对话"""
        payload = self._build_payload(messages, stream=False, **kwargs)
        logger.debug("LLM chat request: model=%s messages=%d", payload["model"], len(messages))

        resp = self._client.post(self._chat_url, headers=self._headers, json=payload)
        resp.raise_for_status()
        body = resp.text
        content_type = (resp.headers.get("content-type") or "").lower()
        if "text/event-stream" in content_type or body.lstrip().startswith("data:"):
            return _aggregate_sse_response(body, self.config.model)

        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"].get("content", "")
        return ChatCompletionResult(
            content=content,
            model=data.get("model", self.config.model),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", ""),
            raw=data,
        )

    def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> Any:
        """流式对话 — 返回迭代器，每项为文本块"""
        payload = self._build_payload(messages, stream=True, **kwargs)
        logger.debug("LLM chat stream: model=%s messages=%d", payload["model"], len(messages))

        with self._client.stream(
            "POST", self._chat_url, headers=self._headers, json=payload
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"]
                        piece = delta.get("content") or ""
                        if piece:
                            yield piece
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    def list_models(self) -> list[dict[str, Any]]:
        """获取可用模型列表"""
        resp = self._client.get(self._models_url, headers=self._headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    def close(self) -> None:
        self._client.close()


# ── 工厂函数 ──────────────────────────────────────────


_default_client: LLMClient | None = None


def get_llm_client(config: LLMConfig | None = None) -> LLMClient:
    """获取全局默认 LLM 客户端"""
    global _default_client
    if config:
        _default_client = LLMClient(config)
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def chat(
    prompt: str,
    system_prompt: str = "",
    config: LLMConfig | None = None,
    **kwargs: Any,
) -> str:
    """快捷对话 — 返回文本"""
    messages = []
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    messages.append(ChatMessage(role="user", content=prompt))
    client = get_llm_client(config)
    result = client.chat(messages, **kwargs)
    return result.content


# ── 兼容层（保持原 QwenClient 接口） ────────────────


class QwenClient:
    """保持向后兼容的 QwenClient 封装

    内部使用 LLMClient，提供 async chat 接口。
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._llm = LLMClient(config or LLMConfig())

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """异步对话 — 被 pipeline 调用（同步 httpx 放入线程池）"""
        chat_msgs = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]

        def _call() -> str:
            result = self._llm.chat(
                chat_msgs,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return result.content

        return await asyncio.to_thread(_call)

    async def chat_stream_messages(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ):
        """异步逐块产出 assistant 文本（用于 WebSocket / SSE 推送）。"""
        import queue
        import threading

        chat_msgs = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        loop = asyncio.get_running_loop()
        q: queue.Queue[str | None | BaseException] = queue.Queue()

        def _producer() -> None:
            try:
                for piece in self._llm.chat_stream(chat_msgs, **kwargs):
                    if piece:
                        loop.call_soon_threadsafe(q.put_nowait, piece)
            except BaseException as exc:
                loop.call_soon_threadsafe(q.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)

        threading.Thread(target=_producer, daemon=True).start()
        while True:
            item = await asyncio.to_thread(q.get)
            if item is None:
                break
            if isinstance(item, BaseException):
                raise item
            yield item

    def close(self) -> None:
        self._llm.close()


def get_qwen_client() -> QwenClient:
    """获取 QwenClient（兼容旧接口）

    配置优先级（从高到低）：
      1. settings.llm_base_url / LLM_BASE_URL → 本地 vLLM 等 OpenAI 兼容端点
      2. settings.coze_integration_api_key → Coze Integration（狼人杀默认）
      3. settings.ark_api_key → 火山方舟
      4. settings.dashscope_api_key → 阿里云 DashScope
      5. settings.qwen_api_key → 通义千问
      6. settings.openai_api_key → OpenAI
    """
    import os

    from app.config import settings

    timeout = int(settings.llm_timeout_seconds)

    # 1) 显式 OpenAI 兼容端点（与仓库根 docker-compose vLLM 同栈）
    base_url = (settings.llm_base_url or os.environ.get("LLM_BASE_URL", "")).strip()
    if base_url:
        api_key = settings.llm_api_key or os.environ.get("LLM_API_KEY", "not-needed")
        model = (
            os.environ.get("LLM_MODEL", "")
            or settings.llm_model
            or settings.coze_integration_model
            or settings.qwen_model
            or settings.ark_model
            or DEFAULT_MODEL
        )
        config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
        )
        return QwenClient(config)

    api_key = ""
    model = settings.coze_integration_model or DEFAULT_MODEL
    resolved_base = settings.coze_integration_base_url or COZE_INTEGRATION_BASE_URL

    if settings.coze_integration_api_key:
        api_key = settings.coze_integration_api_key
        resolved_base = settings.coze_integration_base_url or COZE_INTEGRATION_BASE_URL
        model = settings.coze_integration_model or DEFAULT_MODEL
    elif settings.ark_api_key:
        api_key = settings.ark_api_key
        resolved_base = settings.ark_base_url or DEFAULT_BASE_URL
        model = settings.ark_model or DEFAULT_MODEL
    elif settings.dashscope_api_key:
        api_key = settings.dashscope_api_key
        resolved_base = settings.qwen_base_url
        model = settings.qwen_model
    elif settings.qwen_api_key:
        api_key = settings.qwen_api_key
        resolved_base = settings.qwen_base_url
        model = settings.qwen_model
    elif settings.openai_api_key:
        api_key = settings.openai_api_key
        resolved_base = settings.openai_base_url
        model = settings.llm_model

    if not api_key:
        for env_key, base_url, model_default in (
            (
                "COZE_INTEGRATION_API_KEY",
                settings.coze_integration_base_url or COZE_INTEGRATION_BASE_URL,
                settings.coze_integration_model,
            ),
            ("ARK_API_KEY", settings.ark_base_url or DEFAULT_BASE_URL, settings.ark_model),
            ("DASHSCOPE_API_KEY", settings.qwen_base_url, settings.qwen_model),
            ("QWEN_API_KEY", settings.qwen_base_url, settings.qwen_model),
            ("OPENAI_API_KEY", settings.openai_base_url, settings.llm_model),
        ):
            val = os.environ.get(env_key, "")
            if val:
                api_key = val
                resolved_base = base_url
                model = model_default or DEFAULT_MODEL
                if env_key == "OPENAI_API_KEY":
                    model = os.environ.get("LLM_MODEL", model)
                break

    if not api_key:
        raise LlmNotConfiguredError(
            "LLM 未配置：设置 COZE_INTEGRATION_API_KEY、LLM_BASE_URL 或其它云厂商 Key"
        )

    config = LLMConfig(
        api_key=api_key,
        base_url=resolved_base,
        model=model,
        timeout=timeout,
    )
    return QwenClient(config)