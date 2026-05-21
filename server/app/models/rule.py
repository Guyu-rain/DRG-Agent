"""规则版本 (RuleVersion) ORM 模型。参照 plans/05_data_model.md §2.4。"""

from __future__ import annotations

from functools import partial

from sqlalchemy import JSON, Column, DateTime, String, Text

from app.models.base import Base, generate_id, utcnow


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "RV"))
    version_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    source_filename = Column(String(255), nullable=True)
    source_file_hash = Column(String(80), nullable=True)
    status = Column(String(20), nullable=False, default="imported", index=True)

    parse_errors = Column(JSON, nullable=True)

    mdc_list = Column(JSON, nullable=True)
    adrg_list = Column(JSON, nullable=True)
    drg_list = Column(JSON, nullable=True)
    mcc_list = Column(JSON, nullable=True)
    cc_list = Column(JSON, nullable=True)
    exclusion_table = Column(JSON, nullable=True)

    rule_counts = Column(JSON, nullable=True)

    imported_at = Column(DateTime(timezone=True), default=utcnow)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
