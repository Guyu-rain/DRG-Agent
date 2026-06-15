"""文档提交智能体 (规则)。将文档存入虚拟文档系统的文件存储。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.models.base import utcnow

_EXT = {"markdown": "md", "html": "html", "pdf": "md"}


def _safe_filename(text: str, fallback: str) -> str:
    """将标题转为安全的文件名片段 (去除非法字符, 限长)。"""
    cleaned = re.sub(r'[\\/:*?"<>|\n\r\t]+', "_", (text or "").strip())
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._")
    return cleaned[:60] or fallback


def submit_document(
    doc_id: str, doc_type: str, content: str, version: str = "V1.0", title: str | None = None
) -> dict:
    """将文档写入虚拟文档系统的文件存储 (documents/generated), 返回提交记录。

    所有生成文档统一扁平存放于 generated/ 下, 文件名以可读标题命名,
    类型仅作内容标签 (不再按类型分子目录)。

    Returns:
        {"file_path", "file_format", "file_size", "checksum", "submitted_at"}
    """
    generated_dir = settings.document_generated_dir
    generated_dir.mkdir(parents=True, exist_ok=True)

    file_format = "markdown"
    name = _safe_filename(title or doc_id, doc_id)
    filename = f"{name}_{version}.{_EXT[file_format]}"
    file_path = generated_dir / filename

    data = content.encode("utf-8")
    file_path.write_bytes(data)
    checksum = "sha256:" + hashlib.sha256(data).hexdigest()

    logger.info(f"文档已提交至虚拟文档系统: {file_path}")
    return {
        "file_path": str(file_path),
        "file_format": file_format,
        "file_size": len(data),
        "checksum": checksum,
        "submitted_at": utcnow(),
    }


def read_submitted_document(file_path: str) -> str | None:
    """读取已提交文档的内容。"""
    path = Path(file_path)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
