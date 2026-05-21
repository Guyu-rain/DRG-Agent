"""Prompt 模板加载与渲染。"""

from pathlib import Path
from string import Template

_PROMPT_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """读取 ``<name>.txt`` 模板原文。"""
    path = _PROMPT_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {name}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **kwargs) -> str:
    """使用 ``$变量`` 占位符渲染 Prompt 模板。"""
    return Template(load_prompt(name)).safe_substitute(**kwargs)


__all__ = ["load_prompt", "render_prompt"]
