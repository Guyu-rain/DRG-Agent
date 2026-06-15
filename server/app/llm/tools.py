"""LLM Function Calling 工具定义与执行。

提供 read_source_file / list_source_files / search_code 三个工具,
供 LLM 在文档生成和问答时自主查阅项目源代码。
"""

from __future__ import annotations

import re
import subprocess  # noqa: S404 - ripgrep 为开发工具, 无外部输入风险
from inspect import Parameter, signature
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger

_REPO_ROOT = settings.repo_root
_MAX_FILE_LINES = 300
# Python 回退搜索时跳过的目录与仅纳入的文本后缀
_SKIP_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".pnpm-store", ".uv-cache",
    "dist", "build", ".mypy_cache", ".ruff_cache", ".pytest_cache",
}
_TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".txt", ".md", ".json", ".css", ".yaml", ".yml"}

# ------------------------------------------------------------------ 工具 Schema
SOURCE_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_source_file",
            "description": (
                "读取 DRG-Agent 项目中指定路径的源代码文件, 返回文件前 N 行内容。"
                "用于查阅具体模块的实现细节、类定义、函数签名等。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于项目根目录的文件路径, 如 server/app/engine/mdc_matcher.py",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": f"最大返回行数, 默认 {_MAX_FILE_LINES}",
                        "default": _MAX_FILE_LINES,
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "从第几行开始读取，默认为第 1 行",
                        "default": 1,
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_source_files",
            "description": (
                "列出 DRG-Agent 项目中指定子目录的文件结构。"
                "用于了解项目有哪些模块、文件分布, 为进一步 read_source_file 提供路径参考。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "相对于项目根目录的子目录, 如 server/app/engine 或 web/src/pages",
                        "default": "server/app",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "在 DRG-Agent 项目中搜索包含特定关键词/正则模式的代码行。"
                "用于快速定位某个类、函数、变量定义的位置。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索关键词或正则表达式, 如 'class GroupingEngine' 或 'def match_mdc'",
                    },
                    "directory": {
                        "type": "string",
                        "description": "限制搜索的目录, 如 server/app/engine, 默认搜索 server/ 和 web/src/",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]

# ------------------------------------------------------------------ 安全校验
def _safe_path(rel_path: str) -> Path:
    """将相对路径解析为绝对路径, 并强制限制在仓库根目录内。"""
    resolved = (_REPO_ROOT / rel_path).resolve()
    if resolved != _REPO_ROOT and not resolved.is_relative_to(_REPO_ROOT):
        raise PermissionError(f"路径越界, 不允许访问仓库外的文件: {rel_path}")
    return resolved


def _safe_subdir(rel_dir: str) -> Path:
    """同 _safe_path, 但确保目标为目录。"""
    resolved = _safe_path(rel_dir)
    if resolved.exists() and not resolved.is_dir():
        raise ValueError(f"路径不是目录: {rel_dir}")
    return resolved


# ------------------------------------------------------------------ 工具执行
def execute_read_source_file(
    path: str,
    max_lines: int = _MAX_FILE_LINES,
    start_line: int = 1,
) -> str:
    """读取源文件并返回内容。"""
    target = _safe_path(path)
    if not target.exists():
        return f"[错误] 文件不存在: {path}"
    if not target.is_file():
        return f"[错误] 路径不是文件: {path}"
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return f"[错误] 无法以 UTF-8 解码: {path}"
    total = len(lines)
    safe_start = max(int(start_line), 1)
    safe_limit = max(int(max_lines), 1)
    selected = lines[safe_start - 1 : safe_start - 1 + safe_limit]
    return _format_file_output(path, selected, total, len(selected), safe_start)


def execute_list_source_files(directory: str = "server/app") -> str:
    """列出目录结构。"""
    target = _safe_subdir(directory)
    if not target.exists():
        return f"[错误] 目录不存在: {directory}"
    lines: list[str] = [f"目录 {directory} 的文件结构:"]
    try:
        for item in sorted(target.rglob("*")):
            rel = item.relative_to(target)
            prefix = "📁" if item.is_dir() else "📄"
            if item.is_dir() and item.name.startswith((".", "__pycache__")):
                continue
            lines.append(f"  {prefix} {rel}")
    except PermissionError:
        return f"[错误] 无权访问目录: {directory}"
    if len(lines) == 1:
        lines.append("  (空目录)")
    return "\n".join(lines[:200])  # 防止过长


def execute_search_code(pattern: str, directory: str | None = None) -> str:
    """在项目中搜索代码。优先用 ripgrep, 未安装时回退到纯 Python 搜索。"""
    # 每个搜索目录是独立的 rg 位置参数 (不能拼成一个字符串, 否则被当成单一路径)
    search_dirs = [directory] if directory else ["server", "web/src"]

    args = [
        "rg", "--line-number", "--no-heading", "--color=never",
        "--max-count=30",
        pattern, *search_dirs,
    ]
    try:
        result = subprocess.run(  # noqa: S603
            args, capture_output=True, text=True, timeout=10, cwd=str(_REPO_ROOT),
        )
    except FileNotFoundError:
        return _python_search(pattern, search_dirs)  # 无 ripgrep, 纯 Python 回退
    except subprocess.TimeoutExpired:
        return f"[提示] 搜索超时: {pattern}"

    output = result.stdout.strip()
    if not output:
        return f"[提示] 未找到匹配 '{pattern}' 的代码。"
    lines = output.splitlines()
    return f"搜索 '{pattern}' 找到 {len(lines)} 行匹配:\n```\n{chr(10).join(lines[:50])}\n```"


def _python_search(pattern: str, search_dirs: list[str]) -> str:
    """ripgrep 不可用时的纯 Python 搜索 (按正则, 失败则退化为子串匹配)。"""
    try:
        regex = re.compile(pattern)
    except re.error:
        regex = re.compile(re.escape(pattern))

    hits: list[str] = []
    for rel_dir in search_dirs:
        root = _safe_path(rel_dir)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in _TEXT_SUFFIXES:
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            try:
                for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if regex.search(line):
                        rel = path.relative_to(_REPO_ROOT)
                        hits.append(f"{rel}:{lineno}:{line.strip()[:200]}")
                        if len(hits) >= 50:
                            break
            except (UnicodeDecodeError, OSError):
                continue
            if len(hits) >= 50:
                break
        if len(hits) >= 50:
            break

    if not hits:
        return f"[提示] 未找到匹配 '{pattern}' 的代码。"
    return f"搜索 '{pattern}' 找到 {len(hits)} 行匹配:\n```\n{chr(10).join(hits)}\n```"


# ------------------------------------------------------------------ 工具调度
_TOOL_EXECUTORS: dict[str, Any] = {
    "read_source_file": execute_read_source_file,
    "list_source_files": execute_list_source_files,
    "search_code": execute_search_code,
}


def execute_tool_call(tool_name: str, arguments: dict) -> str:
    """根据工具名分发执行, 返回字符串结果。"""
    executor = _TOOL_EXECUTORS.get(tool_name)
    if executor is None:
        return f"[错误] 未知工具: {tool_name}"
    try:
        parameters = signature(executor).parameters
        accepts_kwargs = any(p.kind == Parameter.VAR_KEYWORD for p in parameters.values())
        safe_arguments = (
            arguments
            if accepts_kwargs
            else {key: value for key, value in arguments.items() if key in parameters}
        )
        ignored = sorted(set(arguments) - set(safe_arguments))
        if ignored:
            logger.warning(f"工具 {tool_name} 忽略未知参数: {ignored}")
        result = executor(**safe_arguments)
        logger.info(f"工具调用 {tool_name}({safe_arguments}) -> {len(result)} 字符")
        return result
    except (PermissionError, ValueError) as exc:
        return f"[安全限制] {exc}"
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"工具执行异常 {tool_name}: {exc}")
        return f"[工具异常] {exc}"


def format_file_output(
    path: str,
    lines: list[str],
    total: int,
    shown: int,
    start_line: int = 1,
) -> str:
    """格式化文件输出。"""
    body = "\n".join(f"{i:>4}|{line}" for i, line in enumerate(lines, start_line))
    if start_line > 1 or start_line - 1 + shown < total:
        end_line = start_line + max(shown - 1, 0)
        body += f"\n  ... (共 {total} 行, 显示第 {start_line}-{end_line} 行)"
    return f"文件 {path} (共 {total} 行):\n```\n{body}\n```"


def _format_file_output(
    path: str,
    lines: list[str],
    total: int,
    shown: int,
    start_line: int = 1,
) -> str:
    return format_file_output(path, lines, total, shown, start_line)
