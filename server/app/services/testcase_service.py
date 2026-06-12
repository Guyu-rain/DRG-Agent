"""测试用例服务层。参照 plans/03_api_interfaces.md §6。"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ErrorCode, NotFoundException
from app.core.logging import logger
from app.engine.grouping_engine import GroupingEngine
from app.models import ExecutionLog, TestCase, TestTask, utcnow
from app.services.rule_service import RuleService, index_from_version, parsed_rules_from_version


class TestCaseService:
    """测试用例的生成、查询、导出与提交。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.rule_service = RuleService(db)

    async def generate_testcases(self, payload: dict) -> TestTask:
        """同步生成测试用例，供服务层测试和显式同步调用使用。"""
        task = await self.create_generation_task(payload)
        await self.run_generation(task)
        return task

    async def create_generation_task(self, payload: dict) -> TestTask:
        """创建待执行的测试用例生成任务。"""
        rule_version_id = payload.get("rule_version_id") or payload.get("ruleVersionId")
        scenario_types = payload.get("scenario_types") or payload.get("scenarioTypes") or [
            "normal", "boundary", "abnormal",
        ]
        scope = payload.get("scope") or {}
        sample_case_ids = payload.get("sample_case_ids") or payload.get("sampleCaseIds") or []
        max_count = payload.get("max_count") or payload.get("maxCount") or 50

        task = TestTask(
            rule_version_id=rule_version_id,
            scenario_types=scenario_types,
            scope=scope,
            sample_case_ids=sample_case_ids,
            max_count=max_count,
            status="pending",
            started_at=utcnow(),
        )
        self.db.add(task)
        await self.db.flush()
        self.db.add(ExecutionLog(
            level="info",
            agent="testcase_service",
            task_id=task.id,
            message="测试用例生成任务已入队",
            input_summary=str({
                "scenarioTypes": scenario_types,
                "scope": scope,
                "maxCount": max_count,
            }),
        ))
        return task

    async def run_generation(self, task: TestTask) -> list[TestCase]:
        """执行测试用例生成工作流并落库 (供服务层与 Celery 任务共用)。"""
        from app.agents import get_orchestrator

        task.status = "running"
        await self.db.commit()
        version = None
        if task.rule_version_id:
            version = await self.rule_service.get_version(task.rule_version_id)
        else:
            version = await self.rule_service.get_active_version()
        if version is None:
            task.status = "failed"
            task.error_message = "没有可用的规则版本"
            task.finished_at = utcnow()
            return []

        rule_index = index_from_version(version)
        parsed_rules = parsed_rules_from_version(version)
        try:
            orchestrator = get_orchestrator()
            state = await asyncio.to_thread(
                orchestrator.execute_test_gen,
                version.id, task.scenario_types or [], task.scope or {},
                task.sample_case_ids or [], task.max_count or 50, rule_index, parsed_rules,
            )
            await self.db.refresh(task, attribute_names=["status", "finished_at"])
            if task.status == "cancelled":
                task.finished_at = task.finished_at or utcnow()
                self.db.add(ExecutionLog(
                    level="info",
                    agent="testcase_service",
                    task_id=task.id,
                    message="测试用例生成任务已取消，丢弃生成结果",
                ))
                logger.info(f"测试用例生成结果因任务取消被丢弃: {task.id}")
                return []

            generated = state.get("test_cases") or []
            created: list[TestCase] = []
            for item in generated:
                tc = TestCase(
                    test_task_id=task.id,
                    title=item.get("title", "测试用例"),
                    scenario_type=item.get("scenarioType", "normal"),
                    priority=item.get("priority", "medium"),
                    requirement_ref=item.get("requirementRef"),
                    rule_version_id=version.id,
                    input_case=item.get("inputCase"),
                    expected_result=item.get("expectedResult"),
                    expected_explanation=item.get("expectedExplanation"),
                )
                self.db.add(tc)
                created.append(tc)
            task.generated_count = len(created)
            task.status = "completed"
            task.finished_at = utcnow()
            await self.db.flush()
            self.db.add(ExecutionLog(
                level="info",
                agent="testcase_service",
                task_id=task.id,
                message=f"测试用例生成完成: {len(created)} 条",
                output_summary=str(len(created)),
            ))
            logger.info(f"测试用例生成完成: {len(created)} 条 <- {task.id}")
            return created
        except Exception as exc:  # noqa: BLE001
            await self.db.refresh(task, attribute_names=["status", "finished_at"])
            if task.status == "cancelled":
                task.finished_at = task.finished_at or utcnow()
                logger.info(f"测试用例任务取消后结束执行: {task.id}")
                return []

            task.status = "failed"
            task.error_message = str(exc)
            task.finished_at = utcnow()
            self.db.add(ExecutionLog(
                level="error",
                agent="testcase_service",
                task_id=task.id,
                message="测试用例生成失败",
                error_detail=str(exc),
            ))
            logger.error(f"测试用例生成失败 {task.id}: {exc}")
            raise

    async def execute_testcase(self, test_case_id: str) -> TestCase:
        """使用测试用例绑定的规则版本执行确定性入组并保存比对结果。"""
        tc = await self.get_testcase(test_case_id)
        version = (
            await self.rule_service.get_version(tc.rule_version_id)
            if tc.rule_version_id
            else await self.rule_service.get_active_version()
        )
        if version is None:
            raise NotFoundException(ErrorCode.RULE_VERSION_NOT_FOUND, "没有可用的规则版本")

        result = GroupingEngine(index_from_version(version)).group(tc.input_case or {})
        actual = self._result_snapshot(result)
        expected = tc.expected_result or {}
        tc.actual_result = actual
        tc.is_passed = self._matches_expected(expected, actual)
        tc.executed_at = utcnow()
        self.db.add(ExecutionLog(
            level="info" if tc.is_passed else "warning",
            agent="testcase_service",
            task_id=tc.test_task_id,
            message=f"测试用例执行{'通过' if tc.is_passed else '失败'}: {tc.id}",
            input_summary=tc.id,
            output_summary=str(actual),
        ))
        await self.db.flush()
        return tc

    @staticmethod
    def _result_snapshot(result: dict) -> dict:
        if result.get("is_grouped"):
            return {
                "isGrouped": True,
                "mdc": result.get("mdc_code"),
                "adrg": result.get("adrg_code"),
                "drg": result.get("drg_code"),
                "complication": result.get("complication"),
            }
        return {
            "isGrouped": False,
            "stage": result.get("stage"),
            "error": result.get("ungrouped_reason"),
        }

    @staticmethod
    def _matches_expected(expected: dict, actual: dict) -> bool:
        keys = ("isGrouped", "mdc", "adrg", "drg", "complication", "stage")
        return all(expected.get(key) == actual.get(key) for key in keys if key in expected)

    async def get_task(self, test_task_id: str) -> TestTask:
        task = await self.db.get(TestTask, test_task_id)
        if task is None:
            raise NotFoundException(ErrorCode.TASK_NOT_FOUND, f"测试任务不存在: {test_task_id}")
        return task

    async def get_testcase(self, test_case_id: str) -> TestCase:
        tc = await self.db.get(TestCase, test_case_id)
        if tc is None:
            raise NotFoundException(ErrorCode.TESTCASE_NOT_FOUND, f"测试用例不存在: {test_case_id}")
        return tc

    async def get_testcases(
        self, page: int = 1, page_size: int = 20,
        scenario_type: str | None = None, rule_version_id: str | None = None,
    ) -> tuple[list[TestCase], int]:
        stmt = select(TestCase)
        count_stmt = select(func.count()).select_from(TestCase)
        if scenario_type:
            stmt = stmt.where(TestCase.scenario_type == scenario_type)
            count_stmt = count_stmt.where(TestCase.scenario_type == scenario_type)
        if rule_version_id:
            stmt = stmt.where(TestCase.rule_version_id == rule_version_id)
            count_stmt = count_stmt.where(TestCase.rule_version_id == rule_version_id)
        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(TestCase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    async def export_testcases(self, test_case_ids: list[str], fmt: str = "excel") -> str:
        """导出测试用例为 Excel 文件, 返回下载 URL。"""
        from openpyxl import Workbook

        export_dir = settings.document_storage_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "TestCases"
        sheet.append(["用例编号", "标题", "场景类型", "优先级", "需求引用", "预期MDC", "预期ADRG", "预期DRG"])
        for tc_id in test_case_ids:
            tc = await self.db.get(TestCase, tc_id)
            if tc is None:
                continue
            expected = tc.expected_result or {}
            sheet.append([
                tc.id, tc.title, tc.scenario_type, tc.priority, tc.requirement_ref or "",
                expected.get("mdc", ""), expected.get("adrg", ""), expected.get("drg", ""),
            ])

        export_id = f"TEST-EXPORT-{utcnow().strftime('%Y%m%d%H%M%S')}"
        file_path = export_dir / f"{export_id}.xlsx"
        workbook.save(file_path)
        logger.info(f"测试用例已导出: {file_path}")
        return f"/api/v1/testcases/export/{export_id}.xlsx"

    async def create_document_task(
        self, test_case_ids: list[str], doc_title: str, doc_type: str = "testing"
    ):
        """汇总测试用例并创建异步文档任务。"""
        from app.services.document_service import DocumentService

        cases_context = []
        for tc_id in test_case_ids:
            tc = await self.db.get(TestCase, tc_id)
            if tc:
                cases_context.append({
                    "id": tc.id, "title": tc.title, "scenarioType": tc.scenario_type,
                    "expectedResult": tc.expected_result,
                })
        doc_service = DocumentService(self.db)
        return await doc_service.create_generation_task({
            "doc_type": doc_type,
            "title": doc_title,
            "context": {"test_cases": cases_context},
        })

    # --------------------------------------------------------------- 序列化
    @staticmethod
    def to_summary(tc: TestCase) -> dict:
        return {
            "testCaseId": tc.id,
            "title": tc.title,
            "scenarioType": tc.scenario_type,
            "priority": tc.priority,
            "requirementRef": tc.requirement_ref,
            "ruleVersion": tc.rule_version_id,
            "inputCase": tc.input_case,
            "expectedResult": tc.expected_result,
            "expectedExplanation": tc.expected_explanation,
            "actualResult": tc.actual_result,
            "isPassed": tc.is_passed,
            "executedAt": tc.executed_at,
            "createdAt": tc.created_at,
        }

    @classmethod
    def to_detail(cls, tc: TestCase) -> dict:
        detail = cls.to_summary(tc)
        detail["actualResult"] = tc.actual_result
        detail["isPassed"] = tc.is_passed
        return detail
