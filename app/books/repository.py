"""Async data-access layer for the books domain.

Repository owns SQLAlchemy queries; the router never sees them.
Domain errors (BookNotFoundError, DuplicateISBNError) are raised here.
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.books.models import Book
from app.books.schemas import BookCreate, BookPatch, BookReplace
from app.exceptions import BookNotFoundError, DuplicateISBNError


class BookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Book]:
        result = await self.session.scalars(select(Book).order_by(Book.id))
        return list(result.all())

    async def get(self, book_id: int) -> Book:
        book = await self.session.get(Book, book_id)
        if book is None:
            raise BookNotFoundError()
        return book

    async def create(self, data: BookCreate) -> Book:
        book = Book(**data.model_dump())
        self.session.add(book)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateISBNError() from exc
        await self.session.refresh(book)
        return book

    async def replace(self, book_id: int, data: BookReplace) -> Book:
        book = await self.get(book_id)
        for field, value in data.model_dump().items():
            setattr(book, field, value)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateISBNError() from exc
        await self.session.refresh(book)
        return book

    async def patch(self, book_id: int, data: BookPatch) -> Book:
        book = await self.get(book_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(book, field, value)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateISBNError() from exc
        await self.session.refresh(book)
        return book

    async def delete(self, book_id: int) -> None:
        result = await self.session.execute(delete(Book).where(Book.id == book_id))
        if result.rowcount == 0:
            raise BookNotFoundError()
