"""数据库引擎与会话配置。"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


def _make_engine(url: str):
    """根据数据库类型创建异步引擎。SQLite 不支持连接池参数。"""
    if url.startswith("sqlite"):
        return create_async_engine(url, echo=False)
    return create_async_engine(url, echo=False, pool_size=5, max_overflow=10, pool_pre_ping=True)


engine = _make_engine(settings.DATABASE_URL)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供一个数据库会话，自动提交/回滚。"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models() -> None:
    """根据 ORM 元数据创建所有表 (开发/演示环境的便捷入口)。"""
    # 确保所有模型已注册到 Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
