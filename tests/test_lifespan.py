"""Test the FastAPI lifespan: startup + shutdown should run cleanly."""
from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


async def test_lifespan_runs_startup_and_shutdown(monkeypatch) -> None:
    """LifespanManager (via AsyncClient) drives both startup and shutdown."""
    monkeypatch.setenv("APP_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    app = create_app(settings)

    transport = ASGITransport(app=app)
    # NOTE: AsyncClient as a context manager does NOT run lifespan;
    # explicitly trigger lifespan startup via the ASGI scope.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _run_lifespan():
        async with app.router.lifespan_context(app):
            yield

    async with _run_lifespan():
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            resp = await ac.get("/")
            assert resp.status_code == 200
