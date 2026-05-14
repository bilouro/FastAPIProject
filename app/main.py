"""FastAPI application factory and ASGI entrypoint."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.books.router import router as books_router, sleep_router
from app.config import Settings, get_settings
from app.database import dispose_engine, get_session
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging

log = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("starting app env=%s version=%s", settings.env, __version__)
    try:
        yield
    finally:
        log.info("shutting down")
        await dispose_engine()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Lets tests inject a tailored Settings instance; production calls it with no args.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title="Books API",
        version=__version__,
        description=(
            "Async REST API for managing books. "
            "Built with FastAPI, SQLAlchemy 2 async, asyncpg, and Alembic."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def add_server_timing(request: Request, call_next):
        t0 = perf_counter()
        response = await call_next(request)
        response.headers["X-Response-Time"] = f"{(perf_counter() - t0) * 1000:.3f}"
        return response

    register_exception_handlers(app)
    app.include_router(books_router, prefix="/v1")
    app.include_router(sleep_router, prefix="/v1")

    @app.get("/health", tags=["meta"], summary="Liveness + DB readiness probe")
    async def health(
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> dict[str, str]:
        db_status = "ok"
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            log.exception("health check: database query failed")
            db_status = "error"
        return {"status": "ok", "database": db_status, "version": __version__}

    @app.get(
        "/swagger.json",
        include_in_schema=False,
        summary="OpenAPI spec alias (compatibility with Flask predecessor)",
    )
    async def swagger_json() -> dict:
        return app.openapi()

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "Books API",
            "version": __version__,
            "api": "/v1",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104
