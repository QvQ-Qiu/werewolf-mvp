"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.library_routes import router as library_router
from app.api.routes import router as rest_router
from app.api.websocket import router as ws_router
from app.config import settings
from app.skills.openclaw import openclaw_adapter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 — 启动时注册内置 Skills"""
    import logging

    from app.llm.health import llm_status, probe_llm, reset_llm_probe_cache

    openclaw_adapter.initialize()
    reset_llm_probe_cache()
    probe_llm(force=True)
    status = llm_status()
    log = logging.getLogger("app.main")
    if status["configured"] and not status["reachable"]:
        log.error(
            "LLM 已配置但无法连通，AI 将使用 Mock。请检查 .env 中的 ARK_API_KEY：%s",
            status.get("error"),
        )
    elif status["reachable"]:
        log.info("LLM 已就绪 provider=%s", status.get("provider"))
    yield


app = FastAPI(
    title="十人狼人杀 MVP",
    description="1 人 + 9 AI 预女猎守狼人杀 | MCP / CLI / Skills / OpenClaw / Coze CLI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)
app.include_router(library_router)
app.include_router(ws_router)

# Skills 系统
from app.skills.routes import router as skills_router
app.include_router(skills_router)

# OpenClaw 集成
from app.skills.openclaw_routes import router as openclaw_router
app.include_router(openclaw_router)

# MCP SSE 路由（可选，仅在需要时启用）
from app.mcp.routes import router as mcp_router
app.include_router(mcp_router)

# Coze CLI 集成
from app.skills.coze.routes import router as coze_router
app.include_router(coze_router)

# LLM API 集成
from app.llm.routes import router as llm_router
app.include_router(llm_router)

# 生产：托管前端构建产物（API 路由已先注册，优先匹配）
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if settings.serve_frontend_dist and _frontend_dist.is_dir():
    assets = _frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(
            ("api/", "ws/", "skills", "mcp", "openclaw", "coze", "llm", "libraries")
        ):
            from fastapi import HTTPException

            raise HTTPException(status_code=404)
        index = _frontend_dist / "index.html"
        if full_path and (_frontend_dist / full_path).is_file():
            return FileResponse(_frontend_dist / full_path)
        return FileResponse(index)