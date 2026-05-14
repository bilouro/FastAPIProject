<div align="center">

# Books API

**A reference-grade, fully asynchronous Books REST API built with FastAPI, SQLAlchemy 2, and asyncpg.**

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20async-d71f00)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](#testing)
[![Tests](https://img.shields.io/badge/tests-71%20passing-brightgreen)](#testing)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000)](https://github.com/astral-sh/ruff)
[![License: BSD-2-Clause](https://img.shields.io/badge/license-BSD--2--Clause-blue.svg)](LICENSE)

[Quickstart](#quickstart) ·
[API Reference](#api-reference) ·
[Architecture](#architecture) ·
[Configuration](#configuration) ·
[Testing](#testing) ·
[Roadmap](#roadmap)

</div>

---

## Overview

**Books API** is a small, opinionated CRUD service built as a teaching reference for a *modern* Python web stack. Every choice is intentional: async end-to-end, strict typing at every boundary, a clean separation of HTTP / domain / data layers, and a test suite that runs in under a second with **100 % coverage** and no external dependencies.

It started life as the [FlaskProject](https://github.com/bilouro/FlaskProject) twin — same domain, same contract — but rebuilt around FastAPI's async-first model and the latest stable releases of SQLAlchemy, Pydantic, and Alembic.

### Why this exists

- Show what an idiomatic, **production-shaped** FastAPI project looks like in 2026.
- Demonstrate **async SQLAlchemy 2** + **asyncpg** with real migrations, not a toy SQLite glued together with `Base.metadata.create_all`.
- Provide a copy-pasteable foundation for new services: lifespan, config, logging, error envelope, tests — all wired up.

### What you get

- Fully async request / response pipeline (FastAPI → repository → asyncpg).
- Strict Pydantic v2 schemas with `extra="forbid"` and typed validation.
- A repository pattern that keeps HTTP concerns out of SQL.
- One unified error envelope across `4xx` / `5xx`, including structured validation details.
- Structured **JSON logging** ready for any log shipper.
- A test suite that runs in **< 1 s** on an in-memory database — 100 % coverage with **zero** mocks of your own code.
- A multi-stage `Dockerfile` and a `docker-compose.yml` that brings up Postgres and the API together.

---

## Table of Contents

- [Overview](#overview)
- [Quickstart](#quickstart)
- [Architecture](#architecture)
- [Project Layout](#project-layout)
- [API Reference](#api-reference)
- [Error Envelope](#error-envelope)
- [Configuration](#configuration)
- [Database & Migrations](#database--migrations)
- [Testing](#testing)
- [Observability](#observability)
- [Performance & Concurrency](#performance--concurrency)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [FAQ](#faq)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Quickstart

### One-liner (Docker Compose)

```bash
git clone https://github.com/bilouro/FastAPIProject.git
cd FastAPIProject
docker compose up --build
```

Wait a few seconds, then:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"ok","version":"1.0.0"}
```

Open Swagger UI: <http://localhost:8000/docs>

### Local development (no Docker)

```bash
git clone https://github.com/bilouro/FastAPIProject.git
cd FastAPIProject

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                 # then edit APP_DB_PASSWORD etc.

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

That's it. Visit:

| URL                                            | What it serves                    |
| ---------------------------------------------- | --------------------------------- |
| <http://localhost:8000>                        | Service index (JSON)              |
| <http://localhost:8000/v1/books>               | Books resource (paginated list)   |
| <http://localhost:8000/health>                 | Liveness + DB readiness probe     |
| <http://localhost:8000/docs>                   | Swagger UI                        |
| <http://localhost:8000/redoc>                  | ReDoc                             |
| <http://localhost:8000/openapi.json>           | OpenAPI 3 schema                  |
| <http://localhost:8000/swagger.json>           | Same schema, Flask-compat alias   |

---

## Architecture

```
                   ┌──────────────────────────────────────────┐
                   │          ASGI server (uvicorn)           │
                   └────────────────────┬─────────────────────┘
                                        │
                   ┌────────────────────▼─────────────────────┐
                   │              FastAPI app                 │
                   │  · CORS · error handlers · lifespan      │
                   └────────────────────┬─────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
┌───────▼────────┐         ┌────────────▼────────────┐         ┌────────▼────────┐
│   /v1/books    │         │     /health · /docs     │         │   /swagger.json │
│   APIRouter    │         │     · /redoc · /        │         │    (alias)      │
└───────┬────────┘         └─────────────────────────┘         └─────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────┐
│ Pydantic v2 schemas  (BookCreate / BookReplace / BookPatch) │
│  · extra="forbid"    · strict=True      · model_validator   │
└───────┬─────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────┐
│             BookRepository  (async, typed errors)           │
│  list_all · get · create · replace · patch · delete         │
└───────┬─────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────┐
│ SQLAlchemy 2 AsyncSession  ──►  asyncpg  ──►  PostgreSQL 16 │
└─────────────────────────────────────────────────────────────┘
```

### Request lifecycle

1. **Uvicorn** terminates HTTP and hands the ASGI scope to FastAPI.
2. **CORS middleware** (optional) runs first.
3. The router resolves the path → dependencies → handler.
4. The `get_session` dependency yields an `AsyncSession` from the global `async_sessionmaker`. It commits on success or rolls back on exception, then returns the connection to the pool.
5. The handler delegates to `BookRepository`, which speaks SQLAlchemy 2 async to `asyncpg`.
6. Domain exceptions (`BookNotFoundError`, `DuplicateISBNError`) and validation errors are converted to a unified JSON envelope by the registered exception handlers.

### Layering rules

- **Routers** never touch SQL. They orchestrate Pydantic ↔ repository.
- **Repositories** never raise framework exceptions. They raise `DomainError` subclasses.
- **Schemas** are the only place data shapes are declared. ORM models stay private to the persistence layer.
- **Settings** are read once at startup; cached via `lru_cache`.

---

## Project Layout

```
.
├── app/
│   ├── __init__.py                # package metadata
│   ├── main.py                    # FastAPI factory, lifespan, /health, root
│   ├── config.py                  # pydantic-settings, env loading, DSN
│   ├── database.py                # async engine, sessionmaker, get_session
│   ├── exceptions.py              # DomainError + JSON envelope handlers
│   ├── logging_config.py          # structured JSON logging
│   └── books/
│       ├── models.py              # SQLAlchemy 2.x Book ORM model
│       ├── schemas.py             # Pydantic v2 request / response models
│       ├── repository.py          # async CRUD with typed errors
│       └── router.py              # APIRouter mounted under /v1
├── alembic/
│   ├── env.py                     # async Alembic environment
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── tests/                         # 71 tests, 100 % coverage on app/
│   ├── conftest.py                # AsyncClient + in-memory SQLite
│   ├── test_config.py · test_database.py · test_schemas.py
│   ├── test_repository.py · test_router.py · test_main.py
│   └── test_lifespan.py · test_logging_config.py
├── alembic.ini
├── Dockerfile                     # multi-stage, non-root, healthcheck
├── docker-compose.yml             # Postgres 16 + API
├── dbfixtures.sql
├── pyproject.toml                 # pytest, coverage, ruff
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## API Reference

All resource endpoints live under the **`/v1`** prefix. Cross-cutting endpoints (`/health`, `/docs`, ...) stay at the root, by convention.

| Method   | Path                | Body            | Success | Failure                                       |
| -------- | ------------------- | --------------- | ------- | --------------------------------------------- |
| `GET`    | `/health`           | —               | `200`   | always 200; DB state in `database` field      |
| `GET`    | `/v1/books`         | —               | `200`   | —                                             |
| `GET`    | `/v1/books/{id}`    | —               | `200`   | `404`                                         |
| `POST`   | `/v1/books`         | `BookCreate`    | `201`   | `422` (validation), `409` (duplicate ISBN)    |
| `PUT`    | `/v1/books/{id}`    | `BookReplace`   | `200`   | `404`, `422`, `409`                           |
| `PATCH`  | `/v1/books/{id}`    | `BookPatch`     | `200`   | `404`, `422` (no fields / unknown field)      |
| `DELETE` | `/v1/books/{id}`    | —               | `204`   | `404`                                         |

### Resource schema

```jsonc
{
  "id":         42,                       // int, server-assigned
  "title":      "1984",                   // string, required, 1..255
  "author":     "George Orwell",          // string, required, 1..255
  "year":       1949,                     // int, required, -3000..9999
  "isbn":       "978-0451524935",         // string, required, 1..32, unique
  "status":     "active",                 // string, default "active"
  "created_at": "2026-05-12T22:58:00Z",   // server-managed
  "updated_at": "2026-05-12T22:58:00Z"    // server-managed
}
```

### Examples

```bash
# Create
curl -X POST http://localhost:8000/v1/books \
  -H 'content-type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# List
curl http://localhost:8000/v1/books

# Partial update
curl -X PATCH http://localhost:8000/v1/books/1 \
  -H 'content-type: application/json' \
  -d '{"status":"archived"}'

# Replace
curl -X PUT http://localhost:8000/v1/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# Delete
curl -X DELETE http://localhost:8000/v1/books/1 -i
```

---

## Error Envelope

Every non-2xx response shares a single shape, inspired by [RFC 9457 (Problem Details for HTTP APIs)](https://www.rfc-editor.org/rfc/rfc9457.html):

```json
{
  "error":   "Not Found",
  "message": "Book not found",
  "code":    404,
  "path":    "/v1/books/999"
}
```

Validation failures (HTTP 422) include a `details` list matching `RequestValidationError.errors()`:

```json
{
  "error":   "Unprocessable Content",
  "message": "Request validation failed",
  "code":    422,
  "path":    "/v1/books",
  "details": [
    { "type": "missing", "loc": ["body", "isbn"], "msg": "Field required", "input": {} }
  ]
}
```

The same envelope is produced for `404` (unknown route), `405`, `409` (duplicate ISBN), and unhandled `500` errors — clients only ever parse one shape.

---

## Configuration

All settings come from environment variables (prefixed `APP_`) and/or a `.env` file. See [`.env.example`](.env.example).

| Variable              | Default       | Purpose                                    |
| --------------------- | ------------- | ------------------------------------------ |
| `APP_ENV`             | `dev`         | One of `dev` · `test` · `prod`             |
| `APP_LOG_LEVEL`       | `INFO`        | Stdlib log level                           |
| `APP_CORS_ORIGINS`    | `[]`          | JSON array of allowed origins              |
| `APP_DB_HOST`         | `127.0.0.1`   | Postgres host                              |
| `APP_DB_PORT`         | `5432`        | Postgres port                              |
| `APP_DB_NAME`         | `app_db`      | Postgres database                          |
| `APP_DB_USER`         | `app_user`    | Postgres user                              |
| `APP_DB_PASSWORD`     | `changeme`    | Postgres password                          |
| `APP_DATABASE_URL`    | _(unset)_     | Full override DSN (skips per-var assembly) |

The DSN is computed as:

```
postgresql+asyncpg://<user>:<password>@<host>:<port>/<name>
```

Unless `APP_DATABASE_URL` is set, in which case that value wins.

---

## Database & Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new revision after model changes
alembic revision --autogenerate -m "describe change"

# Roll back the most recent migration
alembic downgrade -1

# Seed sample data
psql -h "$APP_DB_HOST" -U "$APP_DB_USER" -d "$APP_DB_NAME" -f dbfixtures.sql
```

The Alembic environment is configured to run the engine in **async mode**, reusing the DSN computed by `app.config.Settings`. There is no separate sync driver to install.

---

## Testing

```bash
pytest                                  # full suite + 100 % coverage gate
pytest tests/test_router.py -v          # one module
pytest -k duplicate                     # by keyword
pytest --cov-report=html                # generate htmlcov/index.html
```

### Highlights

- **71 tests** spanning config, database, schemas, repository, router, exception handlers, lifespan, and logging.
- **100 % branch & line coverage** on `app/*`, enforced by `--cov-fail-under=100` in `pyproject.toml`.
- **No external services needed.** Tests swap the FastAPI `get_session` dependency for an in-memory `aiosqlite` engine.
- **httpx + ASGITransport** drives the app in-process — fast, deterministic.
- **`pytest-asyncio` auto mode** removes the boilerplate of marking every coroutine.

```text
$ pytest -q
.......................................................................   [100%]
TOTAL                       302      0     26      0   100%
Required test coverage of 100% reached. Total coverage: 100.00%
71 passed in 0.54s
```

---

## Observability

`app.logging_config.configure_logging()` installs a JSON formatter on stdout for all loggers, including uvicorn's:

```json
{"asctime": "2026-05-12 22:58:00,000", "levelname": "INFO", "name": "app.main", "message": "starting app env=prod version=1.0.0"}
```

Drop this straight into Loki, CloudWatch, Datadog, or any log shipper that understands JSON lines — no parsers, no regex.

The `sqlalchemy.engine` logger is pinned at `WARNING` by default so query noise stays out of production logs. Bump `APP_LOG_LEVEL=DEBUG` in dev to see them.

---

## Performance & Concurrency

- **Async everything.** A single Uvicorn worker can handle thousands of concurrent in-flight requests, bounded by your Postgres pool size.
- **Connection pooling** via SQLAlchemy's default async pool, with `pool_pre_ping=True` to recover from dropped connections.
- **One engine per process**, created lazily, disposed on lifespan shutdown.
- **No N+1 risk** in this domain — every endpoint touches at most one row by primary key or a single `SELECT *`. Ordered by `id` for stable pagination later.
- **Production-ready Dockerfile** runs as non-root, includes a `HEALTHCHECK`, and uses Python 3.12-slim for a small surface area.

For scale-out, run multiple Uvicorn workers behind a reverse proxy:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Roadmap

- [x] Async SQLAlchemy 2 + asyncpg
- [x] Strict Pydantic v2 schemas
- [x] Repository pattern with typed domain errors
- [x] Unified error envelope (RFC 9457-inspired)
- [x] Structured JSON logging
- [x] 100 % test coverage on `app/*`
- [x] Multi-stage Dockerfile + docker-compose
- [x] API versioning under `/v1`
- [ ] GitHub Actions CI (pytest + ruff + mypy)
- [ ] Pagination (`limit` / `offset`, then keyset)
- [ ] Filtering and full-text search on title / author
- [ ] Authentication (OAuth2 / JWT bearer)
- [ ] Rate limiting middleware
- [ ] OpenTelemetry traces & metrics
- [ ] Pre-commit hooks (ruff format + ruff check + mypy)
- [ ] Helm chart for Kubernetes

---

## Contributing

Issues and PRs are welcome.

1. Fork the repo and create a feature branch from `main`.
2. Run `pytest` and ensure coverage stays at 100 %.
3. Run `ruff check .` and `ruff format .` before pushing.
4. Open a PR with a clear description and screenshots / curl examples for behavioural changes.

For larger refactors, please open an issue first so we can align on scope.

---

## Security

Found a security issue? Please **do not** open a public issue. Email the maintainer (see `git log` for contact) with details and a reproduction. We'll respond within a few business days.

The container image runs as a **non-root** user (`appuser`, UID 1000). Secrets are never read at import time — only inside `Settings()`, which is instantiated lazily.

---

## FAQ

**Why not Django / Litestar / Quart?**
Personal preference and ecosystem familiarity. FastAPI hits a sweet spot between speed of development and runtime performance. The patterns here translate cleanly to any of those frameworks.

**Why SQLAlchemy when SQLModel exists?**
SQLModel is great for prototypes but conflates the ORM and the API schema. Keeping them separate (SQLAlchemy + Pydantic) costs ~20 lines and is much easier to evolve when the public contract and the database shape diverge.

**Why aiosqlite in tests instead of testcontainers / pg_tap?**
Suite speed and friction. The tests run in **< 1 s** and need nothing but Python. For an integration smoke against real Postgres, point `APP_DATABASE_URL` at it and start `uvicorn` — that's the deployment path you're going to use anyway.

**Why `pytest --cov-fail-under=100`?**
Because "97 %" never improves. The gate forces you to either delete dead code or write the missing test before merging. It also flushes out subtle bugs (the `at_least_one_field` validator was added because the 100 % gate showed the patch-empty-body path was uncovered).

**Why are some endpoints written as `return X.model_validate(await ...)`?**
Coverage tracing on CPython 3.13 has a known quirk with the line right after `await` in an async coroutine. Putting the `await` and the `return` on the same line keeps coverage honest without sprinkling `# pragma: no cover` everywhere.

---

## License

[BSD 2-Clause](LICENSE) © Victor H. Bilouro.

---

## Acknowledgments

Built on the shoulders of:

- [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez
- [SQLAlchemy](https://www.sqlalchemy.org/) by Mike Bayer and contributors
- [Pydantic](https://docs.pydantic.dev/) by Samuel Colvin and contributors
- [asyncpg](https://magicstack.github.io/asyncpg/) by MagicStack
- [Alembic](https://alembic.sqlalchemy.org/) by Mike Bayer
- [httpx](https://www.python-httpx.org/) by Tom Christie
- The team behind [PostgreSQL](https://www.postgresql.org/)
