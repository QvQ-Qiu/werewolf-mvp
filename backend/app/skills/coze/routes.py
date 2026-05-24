"""Coze CLI API 路由"""

from __future__ import annotations

from fastapi import APIRouter

from app.skills.coze.adapter import (
    check_coze_installed,
    get_coze_version,
    check_auth_status,
    get_config,
    list_organizations,
    list_spaces,
    run_coze_json,
    CozeCLIError,
)
from app.skills.coze.skills import (
    CozeCheckInstalledSkill,
    CozeAuthStatusSkill,
    CozeConfigListSkill,
    CozeOrganizationListSkill,
    CozeSpaceListSkill,
)
from app.skills.registry import skill_registry

router = APIRouter(prefix="/coze", tags=["coze"])


@router.get("/check")
async def coze_check():
    """检查 coze CLI 是否已安装"""
    installed = check_coze_installed()
    version = get_coze_version() if installed else ""
    return {
        "installed": installed,
        "version": version,
        "install_command": "npm install -g @coze/cli",
    }


@router.get("/auth/status")
async def coze_auth_status():
    """检查 Coze 登录状态"""
    return check_auth_status()


@router.get("/config")
async def coze_config():
    """查看 Coze 配置"""
    return {"config": get_config()}


@router.get("/organizations")
async def coze_organizations():
    """列出可用组织"""
    orgs = list_organizations()
    return {"organizations": orgs, "count": len(orgs)}


@router.get("/spaces")
async def coze_spaces():
    """列出可用空间"""
    spaces = list_spaces()
    return {"spaces": spaces, "count": len(spaces)}


@router.post("/execute")
async def coze_execute(body: dict):
    """执行原始 coze 命令"""
    args = body.get("args", "")
    if isinstance(args, str):
        args_list = args.split()
    else:
        args_list = list(args)
    try:
        result = run_coze_json(args_list)
        return {"success": True, "command": f"coze {' '.join(args_list)}", "data": result}
    except CozeCLIError as e:
        return {"success": False, "error": str(e), "exit_code": e.exit_code}


@router.get("/skills")
async def coze_skills():
    """列出所有已注册的 Coze Skills"""
    skills = skill_registry.list("coze")
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
            }
            for s in skills
        ],
        "count": len(skills),
    }