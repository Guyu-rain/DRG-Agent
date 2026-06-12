"""文档系统服务层。参照 plans/03_api_interfaces.md §5。"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCode, NotFoundException
from app.core.logging import logger
from app.models import Document, DocumentTask, DocumentVersion, ExecutionLog, utcnow

_VALID_STATUS = ["draft", "review", "submitted", "archived"]


class DocumentService:
    """文档生成、预览、编辑、提交与查询。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_document(self, payload: dict) -> DocumentTask:
        """同步生成文档，供服务层测试和显式同步调用使用。"""
        task = await self.create_generation_task(payload)
        await self.run_generation(task)
        return task

    async def create_generation_task(self, payload: dict) -> DocumentTask:
        """创建待执行的文档生成任务，不在请求进程中执行 LLM 工作流。"""
        doc_type = payload.get("doc_type") or payload.get("docType") or "requirements"
        title = payload.get("title") or "DRG-Agent 文档"
        context = payload.get("context") or {}
        template = payload.get("template")

        task = DocumentTask(
            doc_type=doc_type, title=title, context=context, template=template,
            status="pending", started_at=utcnow(),
        )
        self.db.add(task)
        await self.db.flush()
        self.db.add(ExecutionLog(
            level="info",
            agent="document_service",
            task_id=task.id,
            message=f"文档生成任务已入队: {title}",
            input_summary=str({"docType": doc_type, "title": title}),
        ))
        return task

    async def run_generation(self, task: DocumentTask) -> Document | None:
        """执行文档生成工作流并落库 (供服务层与 Celery 任务共用)。"""
        from app.agents import get_orchestrator

        task.status = "running"
        await self.db.commit()
        try:
            orchestrator = get_orchestrator()
            state = await asyncio.to_thread(
                orchestrator.execute_document_gen,
                task.doc_type, task.title, task.context or {}, task.template,
            )
            await self.db.refresh(task, attribute_names=["status", "finished_at"])
            if task.status == "cancelled":
                task.finished_at = task.finished_at or utcnow()
                self.db.add(ExecutionLog(
                    level="info",
                    agent="document_service",
                    task_id=task.id,
                    message="文档生成任务已取消，丢弃生成结果",
                ))
                logger.info(f"文档生成结果因任务取消被丢弃: {task.id}")
                return None

            content = state.get("formatted_content") or state.get("generated_content") or ""
            doc = Document(
                doc_type=task.doc_type,
                title=task.title,
                content=content,
                original_content=content,
                status="draft",
                generated_by="文档生成智能体",
                source_task_id=(task.context or {}).get("sourceTaskId"),
                metadata_json={
                    "generatedAt": utcnow().isoformat(),
                    "modelUsed": "deepseek-chat",
                    "docTaskId": task.id,
                },
                sections=[{"id": "sec-1", "title": "正文", "status": "generated"}],
            )
            self.db.add(doc)
            await self.db.flush()
            task.result_doc_id = doc.id
            task.status = "completed"
            task.finished_at = utcnow()
            self.db.add(ExecutionLog(
                level="info",
                agent="document_service",
                task_id=task.id,
                message=f"文档生成完成: {doc.id}",
                output_summary=doc.id,
            ))
            logger.info(f"文档生成完成: {doc.id} <- {task.id}")
            return doc
        except Exception as exc:  # noqa: BLE001
            await self.db.refresh(task, attribute_names=["status", "finished_at"])
            if task.status == "cancelled":
                task.finished_at = task.finished_at or utcnow()
                logger.info(f"文档任务取消后结束执行: {task.id}")
                return None

            task.status = "failed"
            task.error_message = str(exc)
            task.finished_at = utcnow()
            self.db.add(ExecutionLog(
                level="error",
                agent="document_service",
                task_id=task.id,
                message="文档生成失败",
                error_detail=str(exc),
            ))
            logger.error(f"文档生成失败 {task.id}: {exc}")
            raise

    async def get_task(self, doc_task_id: str) -> DocumentTask:
        task = await self.db.get(DocumentTask, doc_task_id)
        if task is None:
            raise NotFoundException(ErrorCode.TASK_NOT_FOUND, f"文档任务不存在: {doc_task_id}")
        return task

    async def get_document(self, doc_id: str) -> Document:
        doc = await self.db.get(Document, doc_id)
        if doc is None:
            raise NotFoundException(ErrorCode.DOCUMENT_NOT_FOUND, f"文档不存在: {doc_id}")
        return doc

    async def edit_document(self, doc_id: str, content: str | None, title: str | None) -> Document:
        """编辑文档, 编辑前自动保存版本快照。"""
        doc = await self.get_document(doc_id)
        self.db.add(DocumentVersion(
            document_id=doc.id, version=doc.version,
            content_snapshot=doc.content, change_description="编辑前快照",
        ))
        if content is not None:
            doc.content = content
        if title is not None:
            doc.title = title
        # 版本号递增 V1.0 -> V1.1
        try:
            major, minor = doc.version.lstrip("V").split(".")
            doc.version = f"V{major}.{int(minor) + 1}"
        except (ValueError, AttributeError):
            doc.version = "V1.1"
        await self.db.flush()
        return doc

    async def submit_document(self, doc_id: str) -> dict:
        """将文档提交到虚拟文档系统 (写入文件存储)。"""
        from app.agents.submit import submit_document as submit_to_storage

        doc = await self.get_document(doc_id)
        record = submit_to_storage(doc.id, doc.doc_type, doc.content, doc.version)
        doc.status = "submitted"
        doc.submitted_at = record["submitted_at"]
        doc.file_path = record["file_path"]
        doc.file_format = record["file_format"]
        doc.file_size = record["file_size"]
        doc.checksum = record["checksum"]
        await self.db.flush()
        return {
            "docId": doc.id,
            "status": doc.status,
            "submittedAt": doc.submitted_at,
            "submissionRecord": {
                "submitter": "用户/文档提交智能体",
                "version": doc.version,
                "filePath": doc.file_path,
                "checksum": doc.checksum,
            },
        }

    async def update_status(self, doc_id: str, status: str) -> Document:
        doc = await self.get_document(doc_id)
        if status not in _VALID_STATUS:
            from app.core.exceptions import BadRequestException

            raise BadRequestException(ErrorCode.REQUIRED_FIELD_MISSING, f"非法文档状态: {status}")
        doc.status = status
        await self.db.flush()
        return doc

    async def delete_document(self, doc_id: str) -> None:
        doc = await self.get_document(doc_id)
        await self.db.delete(doc)
        await self.db.flush()

    async def get_documents(
        self, page: int = 1, page_size: int = 20,
        doc_type: str | None = None, status: str | None = None, keyword: str | None = None,
    ) -> tuple[list[Document], int]:
        stmt = select(Document)
        count_stmt = select(func.count()).select_from(Document)
        if doc_type:
            stmt = stmt.where(Document.doc_type == doc_type)
            count_stmt = count_stmt.where(Document.doc_type == doc_type)
        if status:
            stmt = stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)
        if keyword:
            stmt = stmt.where(Document.title.ilike(f"%{keyword}%"))
            count_stmt = count_stmt.where(Document.title.ilike(f"%{keyword}%"))
        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    async def get_versions(self, doc_id: str) -> list[DocumentVersion]:
        await self.get_document(doc_id)
        stmt = select(DocumentVersion).where(DocumentVersion.document_id == doc_id).order_by(
            DocumentVersion.created_at
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # --------------------------------------------------------------- 序列化
    @staticmethod
    def to_summary(doc: Document) -> dict:
        return {
            "docId": doc.id,
            "title": doc.title,
            "type": doc.doc_type,
            "status": doc.status,
            "version": doc.version,
            "createdAt": doc.created_at,
            "submittedAt": doc.submitted_at,
            "generatedBy": doc.generated_by,
            "fileSize": doc.file_size,
        }

    @staticmethod
    def to_detail(doc: Document) -> dict:
        metadata = dict(doc.metadata_json or {})
        metadata.setdefault("createdAt", doc.created_at)
        metadata.setdefault("generatedBy", doc.generated_by)
        metadata.setdefault("sourceTasks", [doc.source_task_id] if doc.source_task_id else [])
        return {
            "docId": doc.id,
            "title": doc.title,
            "type": doc.doc_type,
            "version": doc.version,
            "status": doc.status,
            "content": doc.content,
            "createdAt": doc.created_at,
            "submittedAt": doc.submitted_at,
            "generatedBy": doc.generated_by,
            "fileSize": doc.file_size,
            "metadata": metadata,
            "sections": doc.sections or [],
        }
