"""Unit tests for BookRepository — exercising every branch."""
from __future__ import annotations

import pytest

from app.books.repository import BookRepository
from app.books.schemas import BookCreate, BookPatch, BookReplace
from app.exceptions import BookNotFoundError, DomainError, DuplicateISBNError


def test_domain_error_custom_message() -> None:
    err = DomainError("custom")
    assert err.message == "custom"
    assert str(err) == "custom"


async def test_list_empty(session) -> None:
    repo = BookRepository(session)
    assert await repo.list_all() == []


async def test_create_and_get_round_trip(session) -> None:
    repo = BookRepository(session)
    created = await repo.create(BookCreate(title="t", author="a", year=2020, isbn="X"))
    await session.commit()

    fetched = await repo.get(created.id)
    assert fetched.isbn == "X"
    assert fetched.status == "active"


async def test_get_raises_when_missing(session) -> None:
    repo = BookRepository(session)
    with pytest.raises(BookNotFoundError):
        await repo.get(999)


async def test_create_duplicate_isbn_raises(session) -> None:
    repo = BookRepository(session)
    await repo.create(BookCreate(title="t", author="a", year=2020, isbn="DUP"))
    await session.commit()

    with pytest.raises(DuplicateISBNError):
        await repo.create(BookCreate(title="t2", author="a2", year=2021, isbn="DUP"))


async def test_replace_success(session) -> None:
    repo = BookRepository(session)
    created = await repo.create(BookCreate(title="t", author="a", year=2020, isbn="R-1"))
    await session.commit()

    replaced = await repo.replace(
        created.id, BookReplace(title="t2", author="a2", year=2025, isbn="R-2")
    )
    assert replaced.title == "t2" and replaced.isbn == "R-2"


async def test_replace_missing_raises(session) -> None:
    repo = BookRepository(session)
    with pytest.raises(BookNotFoundError):
        await repo.replace(
            999, BookReplace(title="t", author="a", year=2020, isbn="N")
        )


async def test_replace_duplicate_isbn_raises(session) -> None:
    repo = BookRepository(session)
    a = await repo.create(BookCreate(title="A", author="a", year=2020, isbn="AAA"))
    await repo.create(BookCreate(title="B", author="b", year=2020, isbn="BBB"))
    await session.commit()

    with pytest.raises(DuplicateISBNError):
        await repo.replace(
            a.id, BookReplace(title="A2", author="a", year=2020, isbn="BBB")
        )


async def test_patch_success(session) -> None:
    repo = BookRepository(session)
    created = await repo.create(BookCreate(title="t", author="a", year=2020, isbn="P-1"))
    await session.commit()

    patched = await repo.patch(created.id, BookPatch(year=2030))
    assert patched.year == 2030
    assert patched.title == "t"  # unchanged


async def test_patch_missing_raises(session) -> None:
    repo = BookRepository(session)
    with pytest.raises(BookNotFoundError):
        await repo.patch(999, BookPatch(year=2030))


async def test_patch_duplicate_isbn_raises(session) -> None:
    repo = BookRepository(session)
    a = await repo.create(BookCreate(title="A", author="a", year=2020, isbn="P-A"))
    await repo.create(BookCreate(title="B", author="b", year=2020, isbn="P-B"))
    await session.commit()

    with pytest.raises(DuplicateISBNError):
        await repo.patch(a.id, BookPatch(isbn="P-B"))


async def test_delete_success(session) -> None:
    repo = BookRepository(session)
    created = await repo.create(BookCreate(title="t", author="a", year=2020, isbn="D-1"))
    await session.commit()

    await repo.delete(created.id)
    with pytest.raises(BookNotFoundError):
        await repo.get(created.id)


async def test_delete_missing_raises(session) -> None:
    repo = BookRepository(session)
    with pytest.raises(BookNotFoundError):
        await repo.delete(999)
