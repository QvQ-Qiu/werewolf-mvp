"""OpenClaw API 路由 — 将狼人杀暴露为 OpenClaw Tool Provider"""

from __future__ import annotations

from fastapi import APIRouter

from app.skills.openclaw import openclaw_adapter

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


@router.get("/config")
async def get_config():
    """返回 OpenClaw 配置（工具列表）"""
    return openclaw_adapter.get_tool_definitions()


@router.post("/execute")
async def execute_tool(body: dict):
    """执行 OpenClaw Tool"""
    name = body.get("name", "")
    arguments = body.get("arguments", {})
    result = await openclaw_adapter.execute_tool(name, arguments)

    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(result, media_type="application/json")


@router.get("/health")
async def health():
    """OpenClaw 适配器健康检查"""
    return {"status": "ok", "adapter": "werewolf", "tools_count": len(openclaw_adapter.get_tool_definitions())}