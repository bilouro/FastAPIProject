"""Test fixtures.

The suite is fully self-contained: it spins up an in-memory aiosqlite DB,
creates the schema from SQLAlchemy metadata, and overrides FastAPI's
`get_session` dependency to use that engine. No external Postgres needed.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure settings are loaded with predictable test values BEFORE app import.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_LOG_LEVEL", "WARNING")
os.environ.setdefault("APP_DB_PASSWORD", "test")

from app import database as db_module  # noqa: E402
from app.books.models import Base  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import get_session  # noqa: E402
from app.main import create_app  # noqa: E402


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session", autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def engine() -> AsyncIterator:
    eng = create_async_engine(TEST_DATABASE_URL, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    """HTTPX async client with a swapped-in DB session dependency."""
    app = create_app()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
    # Reset module-level engine state between tests so production code path stays clean.
    await db_module.dispose_engine()


@pytest_asyncio.fixture
async def seeded_books(session_factory) -> list[int]:
    """Insert two known rows and return their IDs."""
    from app.books.models import Book

    async with session_factory() as s:
        b1 = Book(title="Book 1", author="Author 1", year=2001, isbn="111")
        b2 = Book(title="Book 2", author="Author 2", year=2002, isbn="222")
        s.add_all([b1, b2])
        await s.commit()
        await s.refresh(b1)
        await s.refresh(b2)
        return [b1.id, b2.id]
