"""Pydantic v2 schemas for the books domain."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


_TITLE = Annotated[str, Field(min_length=1, max_length=255)]
_AUTHOR = Annotated[str, Field(min_length=1, max_length=255)]
_ISBN = Annotated[str, Field(min_length=1, max_length=32)]
_YEAR = Annotated[int, Field(ge=-3000, le=9999)]


class BookBase(BaseModel):
    """Strict base — rejects unknown fields and wrong types."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class BookCreate(BookBase):
    title: _TITLE
    author: _AUTHOR
    year: _YEAR
    isbn: _ISBN


class BookReplace(BookCreate):
    """PUT payload: identical contract to create."""


class BookPatch(BookBase):
    title: _TITLE | None = None
    author: _AUTHOR | None = None
    year: _YEAR | None = None
    isbn: _ISBN | None = None
    status: Annotated[str, Field(min_length=1, max_length=32)] | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> BookPatch:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided")
        return self


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    year: int
    isbn: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
