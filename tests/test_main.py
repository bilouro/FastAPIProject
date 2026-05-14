"""App-level tests: factory, /health, /docs, /redoc, error envelopes."""
from __future__ import annotations

from unittest.mock import patch

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


async def test_x_response_time_header_present(client) -> None:
    resp = await client.get("/health")
    assert "x-response-time" in {k.lower() for k in resp.headers}
    assert float(resp.headers["x-response-time"]) >= 0


async def test_sleep_endpoint_returns_slept_ms(client) -> None:
    resp = await client.get("/v1/sleep?ms=1")
    assert resp.status_code == 200
    assert resp.json() == {"slept_ms": 1}


async def test_sleep_endpoint_uses_pg_sleep_on_postgres() -> None:
    """Cover the postgresql dialect branch by faking the session dialect."""
    from unittest.mock import AsyncMock, MagicMock

    from app.books.router import sleep_endpoint

    fake_session = MagicMock()
    fake_session.bind.dialect.name = "postgresql"
    fake_session.execute = AsyncMock(return_value=None)

    result = await sleep_endpoint(ms=5, session=fake_session)

    assert result == {"slept_ms": 5}
    args, _ = fake_session.execute.call_args
    assert "pg_sleep" in str(args[0])
    assert args[1] == {"s": 0.005}


async def test_create_app_default() -> None:
    app = create_app()
    assert app.title == "Books API"


async def test_create_app_with_cors_origins() -> None:
    settings = Settings(cors_origins=["http://example.test"], db_password="x")
    app = create_app(settings)
    # CORS middleware should be present in the stack.
    middlewares = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middlewares


async def test_health_ok(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "version" in body


async def test_health_db_error(client) -> None:
    """If the DB query fails, /health still returns 200 with database=error."""
    from app.books.models import Book  # noqa: F401 — ensure module imported

    async def boom(*_a, **_kw):
        raise RuntimeError("db down")

    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=boom):
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["database"] == "error"


async def test_openapi_endpoint(client) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "Books API"
    assert "/v1/books" in spec["paths"]
    assert "/v1/books/{book_id}" in spec["paths"]


async def test_swagger_json_alias(client) -> None:
    resp = await client.get("/swagger.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "Books API"


async def test_docs_returns_swagger_ui(client) -> None:
    resp = await client.get("/docs")
    assert resp.status_code == 200
    assert "swagger-ui" in resp.text


async def test_redoc_endpoint(client) -> None:
    resp = await client.get("/redoc")
    assert resp.status_code == 200
    assert "redoc" in resp.text.lower()


async def test_root_endpoint(client) -> None:
    resp = await client.get("/")
    body = resp.json()
    assert body["name"] == "Books API"
    assert body["docs"] == "/docs"


async def test_404_handler_unknown_path(client) -> None:
    resp = await client.get("/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["error"] == "Not Found"
    assert body["path"] == "/does-not-exist"


async def test_http_exception_with_headers_preserved() -> None:
    """Exercise the http_exception_handler header-preservation path."""
    app = create_app()

    @app.get("/__teapot__")
    async def teapot() -> None:
        raise HTTPException(
            status_code=418,
            detail="I refuse",
            headers={"x-teapot": "yes"},
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.get("/__teapot__")
    assert resp.status_code == 418
    assert resp.headers.get("x-teapot") == "yes"
    assert resp.json()["message"] == "I refuse"


async def test_http_exception_with_non_string_detail() -> None:
    """detail that's a dict/list ends up under `details`, not `message`."""
    app = create_app()

    @app.get("/__weird__")
    async def weird() -> None:
        raise HTTPException(status_code=400, detail={"field": "bad"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.get("/__weird__")
    body = resp.json()
    assert body["details"] == {"field": "bad"}
    assert body["message"] == "Bad Request"


async def test_unknown_status_code_envelope() -> None:
    """Falls back to 'Error' phrase when the status code is non-standard."""
    app = create_app()

    @app.get("/__weird_code__")
    async def weird_code() -> None:
        raise HTTPException(status_code=499, detail="client closed request")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.get("/__weird_code__")
    assert resp.status_code == 499
    body = resp.json()
    assert body["error"] in {"Error", "Client Closed Request"}


async def test_500_handler_returns_standard_envelope() -> None:
    """Unhandled exceptions surface through the catch-all envelope."""
    app = create_app()

    @app.get("/__boom__")
    async def boom() -> None:
        raise RuntimeError("unexpected")

    async with ASGITransport(app=app, raise_app_exceptions=False) as transport:
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            resp = await ac.get("/__boom__")
    assert resp.status_code == 500
    body = resp.json()
    assert body == {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred.",
        "code": 500,
        "path": "/__boom__",
    }


