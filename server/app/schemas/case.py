"""病历相关 Pydantic Schema。参照 plans/03_api_interfaces.md §2。"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class DiagnosisSchema(CamelModel):
    code: str | None = None
    name: str | None = None
    source_text: str | None = None


class ProcedureSchema(CamelModel):
    code: str | None = None
    name: str | None = None
    level: int | None = None


class CaseCreate(CamelModel):
    """创建病历请求。文本模式提供 rawText, 结构化模式提供 structuredData。"""

    raw_text: str | None = None
    structured_data: dict[str, Any] | None = None
    source_type: str = Field(default="text", description="text | structured")


class CaseUpdate(CamelModel):
    """更新病历 (人工修正解析结果)。"""

    primary_diagnosis: DiagnosisSchema | None = None
    secondary_diagnoses: list[DiagnosisSchema] | None = None
    primary_procedure: ProcedureSchema | None = None
    other_procedures: list[ProcedureSchema] | None = None
    age: int | None = None
    gender: str | None = None
    discharge_type: str | None = None


class CaseSummary(CamelModel):
    case_id: str
    summary: str
    status: str
    created_at: Any | None = None
    grouping_count: int = 0


class CaseDetail(CamelModel):
    case_id: str
    status: str
    source_type: str
    raw_text: str | None = None
    age: int | None = None
    gender: str | None = None
    primary_diagnosis: DiagnosisSchema | None = None
    secondary_diagnoses: list[DiagnosisSchema] = []
    primary_procedure: ProcedureSchema | None = None
    other_procedures: list[ProcedureSchema] = []
    discharge_type: str | None = None
    parse_warnings: list[str] = []
    validation_result: dict[str, Any] | None = None
    created_at: Any | None = None
