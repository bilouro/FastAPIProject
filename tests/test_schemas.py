"""Tests for Pydantic schemas — focused on validation branches."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.books.schemas import BookCreate, BookOut, BookPatch


def test_book_create_valid() -> None:
    b = BookCreate(title="t", author="a", year=2020, isbn="i")
    assert b.title == "t"


def test_book_create_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="extra"):
        BookCreate(title="t", author="a", year=2020, isbn="i", bogus=1)


def test_book_create_year_must_be_integer() -> None:
    with pytest.raises(ValidationError, match="year"):
        BookCreate(title="t", author="a", year="2020", isbn="i")


@pytest.mark.parametrize("field", ["title", "author", "isbn"])
def test_book_create_string_fields_must_be_strings(field: str) -> None:
    payload = {"title": "t", "author": "a", "year": 2020, "isbn": "i"}
    payload[field] = 123
    with pytest.raises(ValidationError):
        BookCreate(**payload)


def test_book_patch_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="At least one field"):
        BookPatch()


def test_book_patch_accepts_partial_update() -> None:
    p = BookPatch(year=2030)
    assert p.model_dump(exclude_unset=True) == {"year": 2030}


def test_book_out_from_attributes() -> None:
    class _Row:
        id = 1
        title = "t"
        author = "a"
        year = 2020
        isbn = "i"
        status = "active"
        created_at = None
        updated_at = None

    out = BookOut.model_validate(_Row())
    assert out.id == 1 and out.status == "active"
