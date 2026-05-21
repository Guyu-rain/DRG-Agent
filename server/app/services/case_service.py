"""病历服务层。参照 plans/02_architecture.md §2.2, plans/03_api_interfaces.md §2。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCode, NotFoundException
from app.core.logging import logger
from app.models import GroupingTask, PatientCase


def _dedup(items: list[dict], key: str = "code") -> list[dict]:
    """基于指定字段去重 (保留首次出现; 无该字段值的条目全部保留)。"""
    seen: set = set()
    result: list[dict] = []
    for item in items:
        value = item.get(key)
        if value and value in seen:
            continue
        if value:
            seen.add(value)
        result.append(item)
    return result


class CaseService:
    """病历的创建、解析、校验与查询。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------- 字段映射层
    @staticmethod
    def _normalize_case_input(data: dict) -> dict:
        """将中文字段名映射为内部英文键名, 并去重重复的诊断/手术。

        参照 plans/05_data_model.md §5 与 plans/06_agent_workflow.md §2.3.1。
        兼容 example/drg_example.json (含编码) 与 drg_example_nocode.json (无编码)。
        """
        if not isinstance(data, dict):
            return {}

        # 已是英文键名 (前端结构化输入) 时直接返回
        if "primaryDiagnosis" in data and "主要诊断" not in data:
            normalized = dict(data)
            normalized["secondaryDiagnoses"] = _dedup(normalized.get("secondaryDiagnoses") or [])
            normalized["otherProcedures"] = _dedup(normalized.get("otherProcedures") or [])
            return normalized

        normalized: dict[str, Any] = {}
        if "性别" in data:
            normalized["gender"] = data["性别"]
        if "年龄" in data:
            normalized["age"] = data["年龄"]
        if "出院方式" in data:
            normalized["dischargeType"] = data["出院方式"]

        def _diag(raw: Any) -> dict:
            if isinstance(raw, str):
                return {"code": None, "name": raw}
            raw = raw or {}
            return {"code": raw.get("疾病编码"), "name": raw.get("疾病名称")}

        def _proc(raw: Any) -> dict:
            if isinstance(raw, str):
                return {"code": None, "name": raw, "level": None}
            raw = raw or {}
            return {
                "code": raw.get("手术编码"),
                "name": raw.get("手术名称"),
                "level": raw.get("手术级别"),
            }

        if "主要诊断" in data:
            normalized["primaryDiagnosis"] = _diag(data["主要诊断"])
        if "次要诊断列表" in data:
            normalized["secondaryDiagnoses"] = _dedup(
                [_diag(d) for d in data["次要诊断列表"] or []]
            )
        if "主要手术" in data:
            normalized["primaryProcedure"] = _proc(data["主要手术"])
        if "其他手术列表" in data:
            normalized["otherProcedures"] = _dedup(
                [_proc(p) for p in data["其他手术列表"] or []]
            )
        return normalized

    # --------------------------------------------------------------- 写操作
    async def create_case(self, payload: dict) -> PatientCase:
        """创建病历。支持 text / structured 两种输入。"""
        source_type = payload.get("source_type") or payload.get("sourceType") or "text"
        case = PatientCase(source_type=source_type)

        structured = payload.get("structured_data") or payload.get("structuredData")
        if structured:
            normalized = self._normalize_case_input(structured)
            self._apply_normalized(case, normalized)
            case.status = "parsed"
            case.parse_result = normalized
        else:
            case.raw_text = payload.get("raw_text") or payload.get("rawText")
            case.status = "created"

        self.db.add(case)
        await self.db.flush()
        logger.info(f"病历已创建: {case.id} ({source_type})")
        return case

    @staticmethod
    def _apply_normalized(case: PatientCase, normalized: dict) -> None:
        """将归一化字典写入 PatientCase 列。"""
        primary = normalized.get("primaryDiagnosis") or {}
        case.primary_diagnosis_code = primary.get("code")
        case.primary_diagnosis_name = primary.get("name")
        case.secondary_diagnoses = normalized.get("secondaryDiagnoses") or []
        proc = normalized.get("primaryProcedure") or {}
        case.primary_procedure_code = proc.get("code")
        case.primary_procedure_name = proc.get("name")
        case.other_procedures = normalized.get("otherProcedures") or []
        if normalized.get("age") is not None:
            case.age = normalized["age"]
        if normalized.get("gender"):
            case.gender = normalized["gender"]
        if normalized.get("dischargeType"):
            case.discharge_type = normalized["dischargeType"]

    async def import_from_example(self, items: list[dict]) -> list[PatientCase]:
        """批量导入 example/*.json 格式的病历列表。"""
        cases: list[PatientCase] = []
        for item in items:
            payload = {k: v for k, v in item.items() if k != "result"}
            case = await self.create_case(
                {"source_type": "structured", "structured_data": payload}
            )
            cases.append(case)
        return cases

    async def parse_case(self, case_id: str) -> dict:
        """解析病历: 文本输入调用病历解析智能体, 结构化输入直接返回。"""
        case = await self.get_case(case_id)
        if case.source_type == "structured" or case.primary_diagnosis_name:
            case.status = "parsed"
            return self._case_to_parsed(case)

        # 文本输入: 调用 LLM 解析
        import asyncio

        from app.agents.case_parser import case_parse_agent
        from app.llm import get_llm_client

        case.status = "parsing"
        state = {"raw_text": case.raw_text, "llm_client": get_llm_client()}
        result = await asyncio.to_thread(case_parse_agent, state)
        parsed = result.get("parsed_case")
        if parsed:
            normalized = self._normalize_case_input(parsed)
            self._apply_normalized(case, normalized)
            case.parse_result = parsed
            case.parse_warnings = parsed.get("warnings", [])
            case.status = "parsed"
        else:
            case.status = "error"
        await self.db.flush()
        return self._case_to_parsed(case)

    async def validate_case(self, case_id: str) -> dict:
        """校验病历编码格式。"""
        from app.engine.code_validator import validate_case_codes

        case = await self.get_case(case_id)
        result = validate_case_codes(self._case_to_parsed(case))
        case.validation_result = result
        case.validation_errors = result["errors"]
        if result["is_valid"] and case.status in ("parsed", "created"):
            case.status = "validated"
        await self.db.flush()
        return result

    async def update_case(self, case_id: str, payload: dict) -> PatientCase:
        """人工修正病历字段。"""
        case = await self.get_case(case_id)
        if "primary_diagnosis" in payload or "primaryDiagnosis" in payload:
            primary = payload.get("primary_diagnosis") or payload.get("primaryDiagnosis") or {}
            case.primary_diagnosis_code = primary.get("code")
            case.primary_diagnosis_name = primary.get("name")
        for key in ("secondary_diagnoses", "secondaryDiagnoses"):
            if key in payload and payload[key] is not None:
                case.secondary_diagnoses = _dedup(payload[key])
        for key in ("primary_procedure", "primaryProcedure"):
            if key in payload and payload[key] is not None:
                proc = payload[key]
                case.primary_procedure_code = proc.get("code")
                case.primary_procedure_name = proc.get("name")
        for key in ("other_procedures", "otherProcedures"):
            if key in payload and payload[key] is not None:
                case.other_procedures = _dedup(payload[key])
        for key in ("age", "gender", "discharge_type"):
            if payload.get(key) is not None:
                setattr(case, key, payload[key])
        await self.db.flush()
        return case

    async def delete_case(self, case_id: str) -> None:
        case = await self.get_case(case_id)
        await self.db.delete(case)
        await self.db.flush()

    # --------------------------------------------------------------- 读操作
    async def get_case(self, case_id: str) -> PatientCase:
        case = await self.db.get(PatientCase, case_id)
        if case is None:
            raise NotFoundException(ErrorCode.CASE_NOT_FOUND, f"病历不存在: {case_id}")
        return case

    async def get_cases(
        self, page: int = 1, page_size: int = 20, status: str | None = None, keyword: str | None = None
    ) -> tuple[list[PatientCase], int]:
        stmt = select(PatientCase)
        count_stmt = select(func.count()).select_from(PatientCase)
        if status:
            stmt = stmt.where(PatientCase.status == status)
            count_stmt = count_stmt.where(PatientCase.status == status)
        if keyword:
            like = f"%{keyword}%"
            cond = PatientCase.primary_diagnosis_code.ilike(like) | PatientCase.primary_diagnosis_name.ilike(like)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(PatientCase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    async def count_groupings(self, case_id: str) -> int:
        stmt = select(func.count()).select_from(GroupingTask).where(GroupingTask.case_id == case_id)
        return (await self.db.execute(stmt)).scalar_one()

    # --------------------------------------------------------------- 工具
    @staticmethod
    def _case_to_parsed(case: PatientCase) -> dict:
        """将 PatientCase 列还原为标准化 parsed_case 字典。"""
        return {
            "primaryDiagnosis": {
                "code": case.primary_diagnosis_code,
                "name": case.primary_diagnosis_name,
            },
            "secondaryDiagnoses": case.secondary_diagnoses or [],
            "primaryProcedure": {
                "code": case.primary_procedure_code,
                "name": case.primary_procedure_name,
            },
            "otherProcedures": case.other_procedures or [],
            "age": case.age,
            "gender": case.gender,
        }

    @staticmethod
    def to_summary(case: PatientCase, grouping_count: int = 0) -> dict:
        return {
            "caseId": case.id,
            "summary": f"主诊断：{case.primary_diagnosis_code or case.primary_diagnosis_name or '(未解析)'}",
            "status": case.status,
            "createdAt": case.created_at,
            "groupingCount": grouping_count,
        }

    @classmethod
    def to_detail(cls, case: PatientCase) -> dict:
        parsed = cls._case_to_parsed(case)
        return {
            "caseId": case.id,
            "status": case.status,
            "sourceType": case.source_type,
            "rawText": case.raw_text,
            "age": case.age,
            "gender": case.gender,
            "primaryDiagnosis": parsed["primaryDiagnosis"],
            "secondaryDiagnoses": parsed["secondaryDiagnoses"],
            "primaryProcedure": parsed["primaryProcedure"],
            "otherProcedures": parsed["otherProcedures"],
            "dischargeType": case.discharge_type,
            "parseWarnings": case.parse_warnings or [],
            "validationResult": case.validation_result,
            "createdAt": case.created_at,
        }
