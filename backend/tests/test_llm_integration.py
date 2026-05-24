"""可选：真实 Qwen API 集成测试（需配置 Key）"""

import os

import pytest

from app.llm.client import get_qwen_client

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not (os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")),
    reason="未配置 QWEN_API_KEY / DASHSCOPE_API_KEY",
)
@pytest.mark.asyncio
async def test_real_qwen_chat() -> None:
    client = get_qwen_client()
    assert client is not None
    reply = await client.chat(
        [{"role": "user", "content": "用一句话说你好"}],
        max_tokens=32,
    )
    assert len(reply) > 0
