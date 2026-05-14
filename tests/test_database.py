"""Tests for app.database module-level engine helpers."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app import database as db_module
from app.config import get_settings


@pytest.fixture(autouse=True)
async def _isolate_module_state(monkeypatch) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()
    await db_module.dispose_engine()
    yield
    await db_module.dispose_engine()
    get_settings.cache_clear()


async def test_get_engine_returns_cached_async_engine() -> None:
    eng1 = db_module.get_engine()
    eng2 = db_module.get_engine()
    assert isinstance(eng1, AsyncEngine)
    assert eng1 is eng2


async def test_get_sessionmaker_returns_cached_factory() -> None:
    sm1 = db_module.get_sessionmaker()
    sm2 = db_module.get_sessionmaker()
    assert isinstance(sm1, async_sessionmaker)
    assert sm1 is sm2


async def test_dispose_engine_resets_state() -> None:
    eng1 = db_module.get_engine()
    await db_module.dispose_engine()
    eng2 = db_module.get_engine()
    assert eng1 is not eng2


async def test_get_session_yields_and_commits() -> None:
    """Drive the get_session dependency directly to cover its commit branch."""
    from sqlalchemy import text

    gen = db_module.get_session()
    session = await anext(gen)
    await session.execute(text("SELECT 1"))
    with pytest.raises(StopAsyncIteration):
        await anext(gen)


async def test_get_session_rolls_back_on_exception() -> None:
    """If the consumer raises, the session must roll back and re-raise."""
    gen = db_module.get_session()
    await anext(gen)
    with pytest.raises(RuntimeError, match="boom"):
        await gen.athrow(RuntimeError("boom"))


async def test_build_engine_postgres_url_path() -> None:
    """Exercise non-sqlite branch of _build_engine without making a real connection."""
    eng = db_module._build_engine("postgresql+asyncpg://u:p@127.0.0.1:5432/db")
    assert isinstance(eng, AsyncEngine)
    await eng.dispose()
