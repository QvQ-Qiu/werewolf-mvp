"""Coze CLI 适配器 — 封装 `coze` 命令的执行与输出解析"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

COZE_BIN = "coze"

DEFAULT_TIMEOUT = 120  # 大多数命令 2 分钟足够
LONG_TIMEOUT = 600     # 长耗时命令（generate video 等）


class CozeCLIError(Exception):
    """Coze CLI 执行异常"""

    def __init__(self, message: str, exit_code: int = -1, stderr: str = "") -> None:
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message)


def _run_coze(
    args: list[str],
    timeout: int = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """执行 `coze` 命令并返回结果"""
    cmd = [COZE_BIN] + args
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    logger.info("执行 coze: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
        )
    except subprocess.TimeoutExpired:
        raise CozeCLIError(f"命令超时 ({timeout}s): {' '.join(cmd)}", exit_code=8)
    except FileNotFoundError:
        raise CozeCLIError(
            f"`{COZE_BIN}` 未找到，请先安装: npm install -g @coze/cli",
            exit_code=-1,
        )

    if result.returncode != 0:
        raise CozeCLIError(
            f"命令失败 (exit={result.returncode}): {result.stderr.strip()}",
            exit_code=result.returncode,
            stderr=result.stderr,
        )

    return result


def run_coze_json(
    args: list[str],
    timeout: int = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
) -> Any:
    """执行 coze 命令并解析 JSON 输出"""
    if "--format" not in args and "--format json" not in " ".join(args):
        args = args + ["--format", "json"]
    result = _run_coze(args, timeout=timeout, env=env)
    stdout = result.stdout.strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # NDJSON 场景（如 message send）按行解析
        lines = [line for line in stdout.split("\n") if line.strip()]
        objects = []
        for line in lines:
            try:
                objects.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        if len(objects) == 1:
            return objects[0]
        return objects


def check_coze_installed() -> bool:
    """检查 coze CLI 是否已安装"""
    try:
        result = subprocess.run(
            [COZE_BIN, "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_coze_version() -> str:
    """获取 coze CLI 版本"""
    try:
        result = _run_coze(["--version"])
        return result.stdout.strip()
    except CozeCLIError:
        return "unknown"


def check_auth_status() -> dict[str, Any]:
    """检查 Coze 登录状态"""
    try:
        data = run_coze_json(["auth", "status"])
        return data
    except CozeCLIError as e:
        return {"status": "error", "message": str(e)}


def run_generate(
    media_type: str,
    prompt: str,
    output_dir: str | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """执行 coze generate 命令"""
    args = ["generate", media_type, prompt]
    if output_dir:
        args.extend(["--output-path", output_dir])
    if extra_args:
        args.extend(extra_args)
    return run_coze_json(args, timeout=LONG_TIMEOUT)


def upload_file(file_path: str) -> dict[str, Any]:
    """执行 coze file upload"""
    return run_coze_json(["file", "upload", file_path])


def get_config() -> dict[str, Any]:
    """获取 coze 配置"""
    try:
        data = run_coze_json(["config", "list"])
        return data
    except CozeCLIError:
        return {}


def list_organizations() -> list[dict[str, Any]]:
    """列出可用组织"""
    data = run_coze_json(["organization", "list"])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("organizations", data.get("data", []))
    return []


def list_spaces() -> list[dict[str, Any]]:
    """列出可用空间"""
    data = run_coze_json(["space", "list"])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("spaces", data.get("data", []))
    return []