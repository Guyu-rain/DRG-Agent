"""系统配置 (SystemConfig) ORM 模型。参照 plans/05_data_model.md §2.14。"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String

from app.models.base import Base, utcnow


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)
    llm_config = Column(JSON, nullable=True)
    storage_config = Column(JSON, nullable=True)
    active_rule_version_id = Column(String(40), nullable=True)
    demo_initialized = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
