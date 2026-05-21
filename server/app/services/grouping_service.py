"""DRG 入组服务层。参照 plans/03_api_interfaces.md §4。"""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ErrorCode, NotFoundException
from app.core.logging import logger
from app.models import ExecutionLog, GroupingResult, GroupingTask, RuleVersion, TaskStep, utcnow
from app.services.case_service import CaseService
from app.services.rule_service import RuleService, index_from_version

_STEP_NAMES = ["case_parse", "code_validate", "rule_retrieve", "drg_grouping", "explain_generate"]


class GroupingService:
    """执行入组工作流并持久化结果。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.case_service = CaseService(db)
        self.rule_service = RuleService(db)

    async def execute_grouping(self, case_id: str, rule_version_id: str | None = None) -> GroupingTask:
        """执行单个病历的 DRG 入组 (同步完成, 任务状态直接落地)。"""
        case = await self.case_service.get_case(case_id)
        version = await self._resolve_rule_version(rule_version_id)

        snapshot = {
            "primaryDiagnosis": case.primary_diagnosis_code or case.primary_diagnosis_name,
            "secondaryDiagnoses": [
                d.get("code") or d.get("name") for d in (case.secondary_diagnoses or [])
            ],
            "primaryProcedure": case.primary_procedure_code or case.primary_procedure_name,
        }
        task = GroupingTask(
            case_id=case_id,
            rule_version_id=version.id,
            status="executing",
            input_snapshot=snapshot,
            started_at=utcnow(),
        )
        self.db.add(task)
        await self.db.flush()

        started = time.perf_counter()
        rule_index = index_from_version(version)
        parsed = CaseService._case_to_parsed(case)
        has_structured = bool(case.primary_diagnosis_code or case.primary_diagnosis_name)

        from app.agents import get_orchestrator

        orchestrator = get_orchestrator()
        state = await asyncio.to_thread(
            orchestrator.execute_grouping,
            case_id,
            version.id,
            rule_index,
            case.raw_text if not has_structured else None,
            parsed if has_structured else None,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        result_data = state.get("grouping_result") or {}
        explanation = state.get("explanation")
        await self._persist_result(task, result_data, explanation, duration_ms, state.get("error"))
        await self._record_steps(task.id, duration_ms)
        await self._log(task.id, result_data)
        await self.db.flush()
        return task

    async def batch_grouping(self, case_ids: list[str], rule_version_id: str | None = None) -> list[GroupingTask]:
        """批量入组。"""
        tasks: list[GroupingTask] = []
        for case_id in case_ids:
            tasks.append(await self.execute_grouping(case_id, rule_version_id))
        return tasks

    async def get_task(self, task_id: str) -> GroupingTask:
        task = await self.db.get(GroupingTask, task_id)
        if task is None:
            raise NotFoundException(ErrorCode.TASK_NOT_FOUND, f"入组任务不存在: {task_id}")
        return task

    async def get_grouping_result(self, task_id: str) -> dict:
        """组装入组结果响应 (参照 plans/03_api_interfaces.md §4.2)。"""
        task = await self.get_task(task_id)
        result = (
            await self.db.execute(select(GroupingResult).where(GroupingResult.task_id == task_id))
        ).scalar_one_or_none()
        version = await self.db.get(RuleVersion, task.rule_version_id) if task.rule_version_id else None

        payload: dict = {
            "taskId": task.id,
            "status": task.status,
            "caseId": task.case_id,
            "ruleVersion": version.version_name if version else None,
            "startedAt": task.started_at,
            "finishedAt": task.finished_at,
            "durationMs": task.duration_ms,
            "inputSnapshot": task.input_snapshot,
            "result": None,
            "error": None,
        }
        if result and result.is_grouped:
            payload["result"] = {
                "mdc": {"code": result.mdc_code, "name": result.mdc_name},
                "adrg": {"code": result.adrg_code, "name": result.adrg_name},
                "drg": {"code": result.drg_code, "name": result.drg_name},
                "complication": result.complication,
                "evidence": result.evidence_chain or [],
                "explanation": result.explanation,
                "candidateRules": result.candidate_rules or [],
                "warnings": result.warnings or [],
            }
        elif result:
            payload["error"] = {
                "type": task.error_type or "NO_RULE_MATCH",
                "stage": (task.error_message or "").split(":")[0] if task.error_message else None,
                "message": result.ungrouped_reason,
                "suggestions": ["检查诊断编码是否正确", "尝试使用结构化输入补充手术信息"],
                "candidateMatches": [],
            }
        return payload

    async def get_tasks(
        self, page: int = 1, page_size: int = 20, status: str | None = None, case_id: str | None = None
    ) -> tuple[list[GroupingTask], int]:
        stmt = select(GroupingTask)
        count_stmt = select(func.count()).select_from(GroupingTask)
        if status:
            stmt = stmt.where(GroupingTask.status == status)
            count_stmt = count_stmt.where(GroupingTask.status == status)
        if case_id:
            stmt = stmt.where(GroupingTask.case_id == case_id)
            count_stmt = count_stmt.where(GroupingTask.case_id == case_id)
        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(GroupingTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    # --------------------------------------------------------------- 内部
    async def _resolve_rule_version(self, rule_version_id: str | None) -> RuleVersion:
        if rule_version_id:
            version = await self.rule_service.get_version(rule_version_id)
            if version.status != "active":
                raise BadRequestException(
                    ErrorCode.RULE_VERSION_INACTIVE,
                    f"规则版本 {rule_version_id} 未激活 (当前状态: {version.status})",
                )
            return version
        version = await self.rule_service.get_active_version()
        if version is None:
            raise BadRequestException(
                ErrorCode.RULE_VERSION_NOT_FOUND, "系统中没有活跃的规则版本，请先导入并激活规则"
            )
        return version

    async def _persist_result(
        self, task: GroupingTask, result_data: dict, explanation: str | None,
        duration_ms: int, error: dict | None,
    ) -> None:
        is_grouped = bool(result_data.get("is_grouped"))
        task.finished_at = utcnow()
        task.duration_ms = duration_ms
        task.status = "completed" if is_grouped else "failed"
        if not is_grouped:
            task.error_type = (error or {}).get("type", "NO_RULE_MATCH")
            task.error_message = f"{result_data.get('stage')}: {result_data.get('ungrouped_reason')}"

        result = GroupingResult(
            task_id=task.id,
            mdc_code=result_data.get("mdc_code"),
            mdc_name=result_data.get("mdc_name"),
            adrg_code=result_data.get("adrg_code"),
            adrg_name=result_data.get("adrg_name"),
            drg_code=result_data.get("drg_code"),
            drg_name=result_data.get("drg_name"),
            is_grouped=is_grouped,
            ungrouped_reason=result_data.get("ungrouped_reason"),
            complication=result_data.get("complication"),
            evidence_chain=result_data.get("evidence") or [],
            explanation=explanation,
            candidate_rules=result_data.get("candidate_rules") or [],
            warnings=result_data.get("warnings") or [],
        )
        self.db.add(result)

    async def _record_steps(self, task_id: str, total_ms: int) -> None:
        """生成 5 个工作流步骤记录 (用于任务详情展示)。"""
        per_step = max(total_ms // len(_STEP_NAMES), 1)
        for order, name in enumerate(_STEP_NAMES):
            self.db.add(TaskStep(
                task_id=task_id,
                step_name=name,
                step_order=order,
                status="completed",
                duration_ms=per_step,
            ))

    async def _log(self, task_id: str, result_data: dict) -> None:
        level = "info" if result_data.get("is_grouped") else "warning"
        message = (
            f"入组完成: {result_data.get('drg_code')}"
            if result_data.get("is_grouped")
            else f"未入组: {result_data.get('ungrouped_reason')}"
        )
        self.db.add(ExecutionLog(
            level=level,
            agent="grouping_service",
            task_id=task_id,
            message=message,
            output_summary=str(result_data.get("drg_code") or result_data.get("stage")),
        ))
        logger.info(f"[{task_id}] {message}")

    @staticmethod
    def to_task_summary(task: GroupingTask) -> dict:
        return {
            "taskId": task.id,
            "type": "grouping",
            "status": task.status,
            "caseId": task.case_id,
            "createdAt": task.created_at,
            "finishedAt": task.finished_at,
            "durationMs": task.duration_ms,
        }
