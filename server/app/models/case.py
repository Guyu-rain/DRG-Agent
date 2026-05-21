"""病历 (PatientCase) ORM 模型。参照 plans/05_data_model.md §2.1。"""

from __future__ import annotations

from functools import partial

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, generate_id, utcnow


class PatientCase(Base):
    __tablename__ = "patient_cases"

    id = Column(String(40), primary_key=True, default=partial(generate_id, "CASE"))
    raw_text = Column(Text, nullable=True)
    source_type = Column(String(20), nullable=False, default="text")
    status = Column(String(20), nullable=False, default="created", index=True)

    patient_id = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)

    primary_diagnosis_code = Column(String(50), nullable=True)
    primary_diagnosis_name = Column(String(200), nullable=True)

    secondary_diagnoses = Column(JSON, nullable=True)
    primary_procedure_code = Column(String(50), nullable=True)
    primary_procedure_name = Column(String(200), nullable=True)
    other_procedures = Column(JSON, nullable=True)

    discharge_type = Column(String(50), nullable=True)

    parse_result = Column(JSON, nullable=True)
    parse_warnings = Column(JSON, nullable=True)

    validation_result = Column(JSON, nullable=True)
    validation_errors = Column(JSON, nullable=True)

    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    grouping_tasks = relationship(
        "GroupingTask", back_populates="case", cascade="all, delete-orphan"
    )
