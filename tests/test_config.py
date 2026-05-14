"""Tests for app.config Settings."""
from __future__ import annotations

import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_build_async_postgres_dsn() -> None:
    s = Settings(db_password="secret", env="dev")
    assert s.sqlalchemy_database_uri.startswith("postgresql+asyncpg://")
    assert "app_user" in s.sqlalchemy_database_uri
    assert "secret" in s.sqlalchemy_database_uri
    assert s.is_test is False


def test_explicit_database_url_takes_precedence() -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.sqlalchemy_database_uri == "sqlite+aiosqlite:///:memory:"


def test_env_test_flag() -> None:
    s = Settings(env="test")
    assert s.is_test is True


def test_get_settings_is_cached(monkeypatch) -> None:
    monkeypatch.setenv("APP_DB_NAME", "cached_db")
    a = get_settings()
    monkeypatch.setenv("APP_DB_NAME", "different_db")
    b = get_settings()
    assert a is b
    assert "cached_db" in a.sqlalchemy_database_uri
