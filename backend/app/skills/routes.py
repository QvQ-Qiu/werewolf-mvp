"""Skills API 路由 — 将 Skills 系统暴露为 REST API"""

from __future__ import annotations

from fastapi import APIRouter

from app.skills.registry import skill_registry

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills():
    """列出所有已注册的 Skills"""
    return {"skills": skill_registry.list_skills_info(), "count": len(skill_registry._skills)}


@router.get("/{name}")
async def get_skill(name: str):
    """获取单个 Skill 详情"""
    skill = skill_registry.get(name)
    if skill is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Skill '{name}' 未找到")
    return {
        "name": skill.name,
        "description": skill.description,
        "version": skill.version,
        "category": skill.category,
    }


@router.post("/{name}/execute")
async def execute_skill(name: str, params: dict | None = None):
    """执行指定 Skill"""
    from app.skills.base import SkillContext

    ctx = SkillContext(params=params or {})
    result = await skill_registry.execute(name, ctx)
    return {"success": result.success, "message": result.message, "data": result.data}