"""HTTP layer: /books CRUD endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.repository import BookRepository
from app.books.schemas import BookCreate, BookOut, BookPatch, BookReplace
from app.database import get_session

router = APIRouter(prefix="/books", tags=["books"])


sleep_router = APIRouter(tags=["bench"])


@sleep_router.get("/sleep", summary="Simulate a slow upstream I/O call")
async def sleep_endpoint(
    ms: int = 50,
    session: Annotated[AsyncSession, Depends(get_session)] = ...,  # type: ignore[assignment]
) -> dict[str, int]:
    """Sleeps inside the DB session (`pg_sleep`) to make every request hold
    a real connection while it waits — the canonical async-vs-sync workload.
    Falls back to `SELECT 1` on dialects without pg_sleep (SQLite in tests)."""
    seconds = max(0, ms) / 1000.0
    dialect = session.bind.dialect.name if session.bind else ""
    if dialect == "postgresql":
        await session.execute(text("SELECT pg_sleep(:s)"), {"s": seconds})
    else:
        await session.execute(text("SELECT 1"))
    return {"slept_ms": ms}


def get_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BookRepository:
    return BookRepository(session)


RepoDep = Annotated[BookRepository, Depends(get_repository)]


@router.get("", response_model=list[BookOut], summary="List all books")
async def list_books(repo: RepoDep) -> list[BookOut]:
    return [BookOut.model_validate(b) for b in await repo.list_all()]


@router.get(
    "/{book_id}",
    response_model=BookOut,
    summary="Get a book by id",
    responses={404: {"description": "Book not found"}},
)
async def get_book(book_id: int, repo: RepoDep) -> BookOut:
    return BookOut.model_validate(await repo.get(book_id))


@router.post(
    "",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a book",
    responses={409: {"description": "Duplicate ISBN"}},
)
async def create_book(payload: BookCreate, repo: RepoDep) -> BookOut:
    return BookOut.model_validate(await repo.create(payload))


@router.put(
    "/{book_id}",
    response_model=BookOut,
    summary="Replace a book (all fields)",
    responses={404: {"description": "Book not found"}, 409: {"description": "Duplicate ISBN"}},
)
async def replace_book(book_id: int, payload: BookReplace, repo: RepoDep) -> BookOut:
    return BookOut.model_validate(await repo.replace(book_id, payload))


@router.patch(
    "/{book_id}",
    response_model=BookOut,
    summary="Partially update a book",
    responses={404: {"description": "Book not found"}, 409: {"description": "Duplicate ISBN"}},
)
async def patch_book(book_id: int, payload: BookPatch, repo: RepoDep) -> BookOut:
    return BookOut.model_validate(await repo.patch(book_id, payload))


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book",
    responses={404: {"description": "Book not found"}},
    response_model=None,
)
async def delete_book(book_id: int, repo: RepoDep) -> None:
    await repo.delete(book_id)
