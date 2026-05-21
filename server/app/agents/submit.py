"""文档提交智能体 (规则)。将文档存入虚拟文档系统的文件存储。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.models.base import utcnow

_EXT = {"markdown": "md", "html": "html", "pdf": "md"}


def submit_document(doc_id: str, doc_type: str, content: str, version: str = "V1.0") -> dict:
    """将文档内容写入文件存储, 返回提交记录。

    Returns:
        {"file_path", "file_format", "file_size", "checksum", "submitted_at"}
    """
    storage_root = settings.document_storage_dir
    type_dir = storage_root / doc_type
    type_dir.mkdir(parents=True, exist_ok=True)

    file_format = "markdown"
    filename = f"{doc_id}_{version}.{_EXT[file_format]}"
    file_path = type_dir / filename

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
