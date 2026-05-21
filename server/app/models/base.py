"""模型层共享工具：ID 生成、时间戳、枚举值。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from app.core.database import Base  # noqa: F401  re-export


def generate_id(prefix: str) -> str:
    """生成带日期与随机后缀的唯一 ID, 如 ``CASE-20260521-A1B2C3``。"""
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{date}-{suffix}"


def utcnow() -> datetime:
    """当前 UTC 时间 (带时区)。"""
    return datetime.now(timezone.utc)


# --- 枚举值定义 (以 String 列存储其 value) ----------------------------------


class CaseStatus(str, Enum):
    CREATED = "created"
    PARSING = "parsing"
    PARSED = "parsed"
    VALIDATED = "validated"
    ERROR = "error"


class SourceType(str, Enum):
    TEXT = "text"
    STRUCTURED = "structured"


class RuleVersionStatus(str, Enum):
    IMPORTED = "imported"
    PARSING = "parsing"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERROR = "error"


class TaskStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ComplicationLevel(str, Enum):
    MCC = "MCC"
    CC = "CC"
    NONE = "NONE"


class DocType(str, Enum):
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TESTING = "testing"
    MANAGEMENT = "management"
    MEETING_MINUTES = "meeting_minutes"
    CONFIGURATION = "configuration"


class DocStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class ScenarioType(str, Enum):
    NORMAL = "normal"
    BOUNDARY = "boundary"
    ABNORMAL = "abnormal"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
