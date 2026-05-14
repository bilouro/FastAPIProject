"""Centralized HTTP error envelope handlers (RFC 9457-inspired).

All errors return:

    {
        "error": "<reason phrase>",
        "message": "<human-readable detail>",
        "code": <int http status>,
        "path": "<request path>",
        "details": <optional list of structured field errors>
    }
"""
from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class DomainError(Exception):
    """Base class for application-level errors that should surface as HTTP."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Internal Server Error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message


class BookNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Book not found"


class DuplicateISBNError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    message = "A book with this ISBN already exists"


def _envelope(status_code: int, message: str, path: str, details: Any = None) -> dict[str, Any]:
    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        phrase = "Error"
    payload: dict[str, Any] = {
        "error": phrase,
        "message": message,
        "code": status_code,
        "path": path,
    }
    if details is not None:
        payload["details"] = details
    return payload


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    details = exc.detail if not isinstance(exc.detail, str) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.status_code, message, request.url.path, details),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_envelope(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            request.url.path,
            details=jsonable_encoder(exc.errors()),
        ),
    )


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.status_code, exc.message, request.url.path),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_envelope(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred.",
            request.url.path,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(DomainError, domain_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
