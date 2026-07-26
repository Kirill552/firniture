from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .settings import settings


def _make_database_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(_make_database_url(), echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# pgvector: без регистрации кодека asyncpg не умеет кодировать list[float]
# в vector — векторный поиск молча возвращает 0 строк (DataError внутри).
from sqlalchemy import event  # noqa: E402


@event.listens_for(engine.sync_engine, "connect")
def _register_pgvector_codec(dbapi_connection, connection_record) -> None:
    from pgvector.asyncpg import register_vector_async

    dbapi_connection.run_async(register_vector_async)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
