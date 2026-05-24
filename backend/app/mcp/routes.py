"""MCP 路由 — 通过 SSE 暴露 MCP Server"""

from __future__ import annotations

from fastapi import APIRouter

from app.mcp.server import mcp

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/tools")
async def list_mcp_tools():
    """列出所有 MCP Tool"""
    tools = []
    for tool in mcp._tool_manager.list_tools():
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        })
    return {"tools": tools, "count": len(tools)}


@router.get("/health")
async def health():
    """MCP 健康检查"""
    return {"status": "ok", "protocol": "mcp", "tools_count": len(mcp._tool_manager.list_tools())}