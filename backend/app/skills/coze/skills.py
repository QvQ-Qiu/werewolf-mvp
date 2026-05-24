"""Coze CLI Skills — 将 coze 命令封装为 BaseSkill"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from app.skills.base import BaseSkill, SkillContext, SkillResult
from app.skills.coze.adapter import (
    COZE_BIN,
    CozeCLIError,
    check_coze_installed,
    check_auth_status,
    get_coze_version,
    get_config,
    list_organizations,
    list_spaces,
    run_coze_json,
    run_generate,
    upload_file,
)


class CozeCheckInstalledSkill(BaseSkill):
    """检查 coze CLI 是否已安装"""

    name = "coze_check_installed"
    description = "检查 coze CLI 是否已安装，返回安装状态和版本号"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        installed = check_coze_installed()
        version = get_coze_version() if installed else ""
        return SkillResult(
            success=True,
            data={
                "installed": installed,
                "version": version,
                "install_command": "npm install -g @coze/cli",
            },
        )


class CozeAuthStatusSkill(BaseSkill):
    """检查 Coze 登录状态"""

    name = "coze_auth_status"
    description = "检查 Coze CLI 登录状态，返回当前认证信息"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        status = check_auth_status()
        return SkillResult(success=True, data=status)


class CozeAuthLoginSkill(BaseSkill):
    """Coze OAuth 登录"""

    name = "coze_auth_login"
    description = "发起 Coze OAuth 登录流程，返回授权链接。需要用户在浏览器中打开链接完成授权"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        try:
            result = run_coze_json(["auth", "login"], timeout=30)
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(
                success=False,
                message=f"登录失败: {e}",
                data={"exit_code": e.exit_code, "stderr": e.stderr},
            )


class CozeConfigListSkill(BaseSkill):
    """查看 Coze 配置"""

    name = "coze_config_list"
    description = "查看当前 Coze CLI 配置项列表"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        config = get_config()
        return SkillResult(success=True, data={"config": config})


class CozeConfigSetSkill(BaseSkill):
    """设置 Coze 配置项"""

    name = "coze_config_set"
    description = "设置 Coze CLI 配置项（key value）"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        key = ctx.params.get("key", "")
        value = ctx.params.get("value", "")
        if not key or value is None:
            return SkillResult(success=False, message="缺少参数: key, value")
        try:
            result = run_coze_json(["config", "set", key, str(value)])
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeOrganizationListSkill(BaseSkill):
    """列出可用组织"""

    name = "coze_organization_list"
    description = "列出当前 Coze 账号下所有可用组织"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        orgs = list_organizations()
        return SkillResult(success=True, data={"organizations": orgs, "count": len(orgs)})


class CozeOrganizationUseSkill(BaseSkill):
    """切换组织"""

    name = "coze_organization_use"
    description = "切换到指定组织（org_id）"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        org_id = ctx.params.get("org_id", "")
        if not org_id:
            return SkillResult(success=False, message="缺少参数: org_id")
        try:
            result = run_coze_json(["organization", "use", org_id])
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeSpaceListSkill(BaseSkill):
    """列出可用空间"""

    name = "coze_space_list"
    description = "列出当前组织下所有可用空间"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        spaces = list_spaces()
        return SkillResult(success=True, data={"spaces": spaces, "count": len(spaces)})


class CozeSpaceUseSkill(BaseSkill):
    """切换空间"""

    name = "coze_space_use"
    description = "切换到指定空间（space_id）"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        space_id = ctx.params.get("space_id", "")
        if not space_id:
            return SkillResult(success=False, message="缺少参数: space_id")
        try:
            result = run_coze_json(["space", "use", space_id])
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeGenerateImageSkill(BaseSkill):
    """使用 Coze 生成图片"""

    name = "coze_generate_image"
    description = "使用 Coze CLI generate image 生成图片，返回图片在线 URL"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        prompt = ctx.params.get("prompt", "")
        if not prompt:
            return SkillResult(success=False, message="缺少参数: prompt（图片描述）")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = run_generate("image", prompt, output_dir=tmpdir)
                # 上传生成的图片
                generated_files = list(Path(tmpdir).iterdir())
                urls = []
                for f in generated_files:
                    upload_result = upload_file(str(f))
                    url = upload_result.get("url", "")
                    if url:
                        urls.append(url)
                return SkillResult(
                    success=True,
                    data={
                        "prompt": prompt,
                        "urls": urls,
                        "raw_result": result,
                    },
                )
            except CozeCLIError as e:
                return SkillResult(success=False, message=str(e))


class CozeGenerateAudioSkill(BaseSkill):
    """使用 Coze 文本转语音"""

    name = "coze_generate_audio"
    description = "使用 Coze CLI generate audio 将文本转为语音，返回音频在线 URL"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        text = ctx.params.get("text", "")
        voice_id = ctx.params.get("voice_id", "")

        if not text:
            return SkillResult(success=False, message="缺少参数: text（要转语音的文本）")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                extra_args = []
                if voice_id:
                    extra_args.extend(["--voice-id", voice_id])
                result = run_generate("audio", text, output_dir=tmpdir, extra_args=extra_args)
                generated_files = list(Path(tmpdir).iterdir())
                urls = []
                for f in generated_files:
                    upload_result = upload_file(str(f))
                    url = upload_result.get("url", "")
                    if url:
                        urls.append(url)
                return SkillResult(
                    success=True,
                    data={
                        "text": text,
                        "urls": urls,
                        "raw_result": result,
                    },
                )
            except CozeCLIError as e:
                return SkillResult(success=False, message=str(e))


class CozeGenerateVideoSkill(BaseSkill):
    """使用 Coze 生成视频"""

    name = "coze_generate_video"
    description = "使用 Coze CLI generate video 生成视频，返回视频在线 URL"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        prompt = ctx.params.get("prompt", "")
        if not prompt:
            return SkillResult(success=False, message="缺少参数: prompt（视频描述）")
        try:
            result = run_coze_json(
                ["generate", "video", "create", prompt, "--wait"],
                timeout=600,
            )
            task_id = ""
            if isinstance(result, dict):
                task_id = result.get("task_id", result.get("taskId", ""))
            return SkillResult(
                success=True,
                data={
                    "prompt": prompt,
                    "task_id": task_id,
                    "raw_result": result,
                },
            )
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeFileUploadSkill(BaseSkill):
    """上传文件到 Coze"""

    name = "coze_file_upload"
    description = "上传本地文件到 Coze 并返回在线访问 URL"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        file_path = ctx.params.get("file_path", "")
        if not file_path:
            return SkillResult(success=False, message="缺少参数: file_path")
        try:
            result = upload_file(file_path)
            return SkillResult(
                success=True,
                data={
                    "url": result.get("url", ""),
                    "uri": result.get("uri", ""),
                    "raw_result": result,
                },
            )
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeCodeProjectCreateSkill(BaseSkill):
    """创建 Coze Coding 项目"""

    name = "coze_code_project_create"
    description = "使用 Coze CLI 创建 Coding 项目（type=web|app）"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        message = ctx.params.get("message", "")
        project_type = ctx.params.get("type", "web")
        if not message:
            return SkillResult(success=False, message="缺少参数: message（项目需求描述）")
        try:
            result = run_coze_json(
                ["code", "project", "create", "--message", message, "--type", project_type],
                timeout=LONG_TIMEOUT,
            )
            project_id = ""
            if isinstance(result, dict):
                project_id = result.get("project_id", result.get("projectId", ""))
            return SkillResult(
                success=True,
                data={
                    "project_id": project_id,
                    "raw_result": result,
                },
            )
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeCodeMessageSendSkill(BaseSkill):
    """发送需求消息到 Coze 项目"""

    name = "coze_code_message_send"
    description = "向指定 Coze Coding 项目发送需求消息"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        message = ctx.params.get("message", "")
        project_id = ctx.params.get("project_id", "")
        if not message or not project_id:
            return SkillResult(success=False, message="缺少参数: message 和 project_id")
        try:
            result = run_coze_json(
                ["code", "message", "send", message, "--project-id", project_id],
                timeout=LONG_TIMEOUT,
            )
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeCodeMessageStatusSkill(BaseSkill):
    """查询 Coze 项目消息状态"""

    name = "coze_code_message_status"
    description = "查询指定 Coze 项目的消息处理状态"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        project_id = ctx.params.get("project_id", "")
        if not project_id:
            return SkillResult(success=False, message="缺少参数: project_id")
        try:
            result = run_coze_json(["code", "message", "status", "--project-id", project_id])
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeCodeDeploySkill(BaseSkill):
    """部署 Coze 项目"""

    name = "coze_code_deploy"
    description = "部署指定 Coze 项目到生产环境"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        project_id = ctx.params.get("project_id", "")
        if not project_id:
            return SkillResult(success=False, message="缺少参数: project_id")
        try:
            result = run_coze_json(
                ["code", "deploy", project_id, "--wait"],
                timeout=LONG_TIMEOUT,
            )
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeCodePreviewSkill(BaseSkill):
    """获取 Coze 项目预览链接"""

    name = "coze_code_preview"
    description = "获取指定 Coze 项目的沙盒预览链接"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        project_id = ctx.params.get("project_id", "")
        if not project_id:
            return SkillResult(success=False, message="缺少参数: project_id")
        try:
            result = run_coze_json(["code", "preview", project_id])
            return SkillResult(success=True, data=result)
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e))


class CozeRawCommandSkill(BaseSkill):
    """执行自定义 coze 命令（高级用户）"""

    name = "coze_raw_command"
    description = "执行任意 coze CLI 原始命令并返回输出（如 coze generate audio \"text\" --output-path /tmp）"
    category = "coze"

    async def execute(self, ctx: SkillContext) -> SkillResult:
        args = ctx.params.get("args", "")
        if not args:
            return SkillResult(success=False, message="缺少参数: args（coze 命令参数列表）")
        if isinstance(args, str):
            args_list = args.split()
        else:
            args_list = list(args)
        try:
            result = run_coze_json(args_list)
            return SkillResult(
                success=True,
                data={"command": f"coze {' '.join(args_list)}", "result": result},
            )
        except CozeCLIError as e:
            return SkillResult(success=False, message=str(e), data={"exit_code": e.exit_code})