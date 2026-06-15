"""pytest fixtures: 测试数据库、HTTP 客户端、规则索引、Mock LLM。"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 确保可导入 server/ 下的 app 与 main
_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

from app.engine.rule_parser import build_rule_index, parse_rule_file  # noqa: E402
from app.llm import MockLLMClient  # noqa: E402

_DEMO_RULES_PATH = _SERVER_DIR / "data" / "rules" / "demo_rules.json"


@pytest.fixture(autouse=True)
def _eager_background_tasks(monkeypatch):
    """接口测试内同步执行后台任务，生产环境仍默认使用 Celery。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TASKS_EAGER", True)


@pytest.fixture(autouse=True)
def _isolated_document_storage(monkeypatch, tmp_path):
    """将文档/导出存储指向临时目录, 避免测试产物污染仓库 documents/。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path / "documents"))


# --- Mock LLM (整个测试会话生效) --------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _mock_orchestrator():
    """用 Mock LLM 替换全局编排器, 避免测试触达真实 LLM API。"""
    import app.agents.orchestration as orch_mod
    from app.agents.orchestration import AgentOrchestrator

    mock_llm = MockLLMClient(default_response="（测试用解释文本）")
    orch_mod._orchestrator = AgentOrchestrator(llm_client=mock_llm)
    yield
    orch_mod._orchestrator = None


# --- 规则引擎 fixtures (无需数据库) ------------------------------------------


@pytest.fixture(scope="session")
def parsed_rules() -> dict:
    return parse_rule_file(_DEMO_RULES_PATH)


@pytest.fixture(scope="session")
def rule_index(parsed_rules: dict) -> dict:
    return build_rule_index(parsed_rules)


@pytest.fixture
def course_case() -> dict:
    """课程示例病历: A01.002+G01* + J96.0 + 38.1000x002 -> BB11。"""
    return {
        "primaryDiagnosis": {"code": "A01.002+G01*", "name": "伤寒性脑膜炎"},
        "secondaryDiagnoses": [{"code": "J96.0", "name": "急性呼吸衰竭"}],
        "primaryProcedure": {"code": "38.1000x002", "name": "动脉内膜剥脱术"},
        "otherProcedures": [],
    }


# --- 数据库 fixtures ---------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """每个测试一个独立的临时 SQLite 数据库。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    os.unlink(path)


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """直接用于服务层测试的数据库会话。"""
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncClient:
    """覆盖 get_db 依赖、连接测试数据库的 HTTP 客户端。"""
    from app.core.database import get_db
    from main import app

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_client(client: AsyncClient) -> AsyncClient:
    """已初始化演示数据 (规则 + 4 个样例病历) 的 HTTP 客户端。"""
    await client.post("/api/v1/system/demo/init")
    return client


@pytest_asyncio.fixture
async def rule_version(db_session):
    """已导入并激活的演示规则版本 (用于服务层测试)。"""
    from app.services.rule_service import RuleService

    service = RuleService(db_session)
    version = await service.import_demo_rules()
    await service.activate_version(version.id)
    await db_session.flush()
    return version
