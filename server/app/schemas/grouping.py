"""DRG 入组相关 Pydantic Schema。参照 plans/03_api_interfaces.md §4。"""

from __future__ import annotations

from typing import Any

from app.schemas.common import CamelModel


class GroupingExecuteRequest(CamelModel):
    case_id: str
    rule_version_id: str | None = None


class BatchGroupingRequest(CamelModel):
    case_ids: list[str]
    rule_version_id: str | None = None


class EvidenceItem(CamelModel):
    step: int
    type: str
    description: str
    matched_code: Any | None = None
    matched_rule: str | None = None
    cc_level: str | None = None
    excluded_by: list[str] | None = None
    excluded: bool | None = None


class CandidateRule(CamelModel):
    adrg: str | None = None
    drg: str | None = None
    name: str | None = None
    reason: str | None = None
    hit: bool | None = None


class GroupingTaskResponse(CamelModel):
    task_id: str
    status: str
    started_at: Any | None = None


class GroupingResultDetail(CamelModel):
    mdc: dict | None = None
    adrg: dict | None = None
    drg: dict | None = None
    complication: str | None = None
    evidence: list[dict] = []
    explanation: str | None = None
    candidate_rules: list[dict] = []
    warnings: list[str] = []


class GroupingResultResponse(CamelModel):
    task_id: str
    status: str
    case_id: str | None = None
    rule_version: str | None = None
    started_at: Any | None = None
    finished_at: Any | None = None
    duration_ms: int | None = None
    result: GroupingResultDetail | None = None
    error: dict | None = None
    input_snapshot: dict | None = None
