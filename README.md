# Books API (FastAPIProject)

This repository implements a **RESTful Books API** using **Python** and **FastAPI**, backed by a **PostgreSQL** database and managed via **Alembic** migrations.

The design emphasizes:

- Clear separation between HTTP layer (FastAPI routers), data-access layer (repository), and persistence (SQLAlchemy models).
- Explicit configuration per environment (Dev, Test, Prod).
- Database schema evolution via migrations.
- Native OpenAPI / Swagger UI via FastAPI's built-in support.
- JSON error handling with a consistent structure.
- Automated tests (unit + functional).

The core domain entity is the `Book`, managed via CRUD endpoints under `/books`.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Technology Stack](#technology-stack)
4. [Prerequisites](#prerequisites)
5. [Configuration](#configuration)
6. [Installation](#installation)
7. [Database Setup & Migrations](#database-setup--migrations)
8. [Running the Application](#running-the-application)
9. [API Usage & Examples](#api-usage--examples)
10. [Testing](#testing)
11. [License](#license)

---

## Project Overview

- **Domain object:** `Book`
  - `id`: integer primary key (auto-increment)
  - `title`: string, required
  - `author`: string, required
  - `year`: integer, required
  - `isbn`: string, required, unique
  - `created_at`: timestamp (set on insert)
  - `updated_at`: timestamp (set on update)
  - `status`: string with default `"active"`

- **Main capabilities:**
  - List, retrieve, create, replace, partially update, and delete books via `/books`.
  - Pydantic validation of incoming JSON payloads.
  - Health check endpoint at `/health`.
  - Swagger UI at `/docs` and ReDoc at `/redoc` — auto-generated from the FastAPI app.
  - Apply database schema changes declaratively using Alembic.

---

## Project Structure

    FastAPIProject
    books/
        __init__.py
        models.py        # SQLAlchemy ORM models
        schemas.py       # Pydantic schemas (request/response)
        repository.py    # Data-access layer
        routes.py        # APIRouter with all /books endpoints
    migrations/
        versions/
        env.py
        script.py.mako
    tests/
        test_app.py             # unit-style
        test_functional_app.py  # integration-style
    alembic.ini
    main.py              # FastAPI app factory, exposes `app`
    config.py            # BaseConfig / DevConfig / TestConfig / ProdConfig
    db.py                # SQLAlchemy engine + session dependency
    dbfixtures.sql       # optional seed data
    README.md

---

## Technology Stack

- **Python 3.10+** — modern type hints, mature ecosystem.
- **FastAPI** — async-first web framework with built-in OpenAPI generation.
- **Uvicorn** — ASGI server for development and production.
- **Pydantic** — request/response validation and serialization.
- **PostgreSQL** — production-grade relational store.
- **SQLAlchemy 2.x** — ORM for `Book` model and queries.
- **Alembic** — versioned schema migrations.
- **pytest** — unit and functional test runner.

---

## Prerequisites

- **Python 3.10+**
- **PostgreSQL** (local or remote)
- **Virtual environment tool** (`python -m venv` recommended)
- **Git**

---

## Configuration

`config.py` reads database settings from environment variables and builds a PostgreSQL DSN:

| Variable | Default |
|---|---|
| `APP_DB_HOST` | `127.0.0.1` |
| `APP_DB_PORT` | `5432` |
| `APP_DB_NAME` | `app_db` |
| `APP_DB_USER` | `app_user` |
| `APP_DB_PASSWORD` | _(none — set it)_ |
| `APP_ENV` | `dev` (one of `dev` / `test` / `prod`) |

These compose into:

    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{name}"

---

## Installation

```bash
git clone https://github.com/bilouro/FastAPIProject.git
cd FastAPIProject
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Database Setup & Migrations

```bash
# Create the database (once)
createdb -h "$APP_DB_HOST" -U "$APP_DB_USER" "$APP_DB_NAME"

# Apply migrations
alembic upgrade head

# (Optional) seed example data
psql -h "$APP_DB_HOST" -U "$APP_DB_USER" -d "$APP_DB_NAME" -f dbfixtures.sql

# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"
```

---

## Running the Application

```bash
# Development (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Then:

- API: <http://localhost:8000/books>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Health: <http://localhost:8000/health>

---

## API Usage & Examples

```bash
# List books
curl http://localhost:8000/books

# Get one
curl http://localhost:8000/books/1

# Create
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# Partial update
curl -X PATCH http://localhost:8000/books/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"archived"}'

# Delete
curl -X DELETE http://localhost:8000/books/1
```

Errors return a consistent JSON shape: `{"detail": "..."}` (with `422` for validation errors and Pydantic field details).

---

## Testing

```bash
pytest                              # full suite
pytest tests/test_app.py            # unit-style
pytest tests/test_functional_app.py # functional
pytest -k "create"                  # by keyword
pytest --cov=books --cov-report=term-missing
```

---

## License

BSD 2-Clause. See [LICENSE](LICENSE).
