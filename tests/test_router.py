"""HTTP-level tests for the /books router."""
from __future__ import annotations

import pytest


async def test_list_books_empty(client) -> None:
    resp = await client.get("/v1/books")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_books_seeded(client, seeded_books) -> None:
    resp = await client.get("/v1/books")
    assert resp.status_code == 200
    data = resp.json()
    assert [b["title"] for b in data] == ["Book 1", "Book 2"]
    expected_keys = {"id", "title", "author", "year", "isbn", "status"}
    assert expected_keys <= set(data[0].keys())


async def test_get_book_success(client, seeded_books) -> None:
    resp = await client.get(f"/v1/books/{seeded_books[0]}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Book 1"


async def test_get_book_not_found(client) -> None:
    resp = await client.get("/v1/books/999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["error"] == "Not Found"
    assert body["message"] == "Book not found"
    assert body["path"] == "/v1/books/999"


async def test_create_book_success(client) -> None:
    payload = {"title": "New", "author": "A", "year": 2023, "isbn": "ZZZ"}
    resp = await client.post("/v1/books", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "New" and body["status"] == "active"
    assert body["id"] > 0


async def test_create_book_duplicate_isbn_returns_409(client) -> None:
    payload = {"title": "x", "author": "a", "year": 2000, "isbn": "DUP"}
    assert (await client.post("/v1/books", json=payload)).status_code == 201
    resp = await client.post("/v1/books", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"] == "Conflict"


async def test_create_book_unknown_field_returns_422(client) -> None:
    payload = {"title": "t", "author": "a", "year": 2020, "isbn": "i", "bogus": 1}
    resp = await client.post("/v1/books", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert any("bogus" in str(d) for d in body["details"])


async def test_create_book_missing_required_returns_422(client) -> None:
    payload = {"title": "t", "author": "a", "year": 2020}
    resp = await client.post("/v1/books", json=payload)
    assert resp.status_code == 422
    assert any("isbn" in str(d) for d in resp.json()["details"])


async def test_create_book_year_must_be_integer(client) -> None:
    payload = {"title": "t", "author": "a", "year": "2020", "isbn": "X"}
    resp = await client.post("/v1/books", json=payload)
    assert resp.status_code == 422
    assert any("year" in str(d) for d in resp.json()["details"])


@pytest.mark.parametrize("field", ["title", "author", "isbn"])
async def test_create_book_string_fields_must_be_strings(client, field: str) -> None:
    payload = {"title": "t", "author": "a", "year": 2020, "isbn": "X"}
    payload[field] = 123
    resp = await client.post("/v1/books", json=payload)
    assert resp.status_code == 422


async def test_create_book_non_object_body_returns_422(client) -> None:
    resp = await client.post("/v1/books", json=["not", "an", "object"])
    assert resp.status_code == 422


async def test_create_book_wrong_content_type_returns_422(client) -> None:
    """FastAPI rejects non-JSON bodies for JSON-typed endpoints with 422."""
    resp = await client.post(
        "/v1/books", content="not-json", headers={"content-type": "text/plain"}
    )
    assert resp.status_code == 422


async def test_replace_book_success(client, seeded_books) -> None:
    payload = {"title": "U", "author": "U", "year": 2010, "isbn": "U-1"}
    resp = await client.put(f"/v1/books/{seeded_books[0]}", json=payload)
    assert resp.status_code == 200
    assert resp.json()["isbn"] == "U-1"


async def test_replace_book_not_found(client) -> None:
    payload = {"title": "x", "author": "x", "year": 2000, "isbn": "N"}
    resp = await client.put("/v1/books/999", json=payload)
    assert resp.status_code == 404


async def test_patch_book_success(client, seeded_books) -> None:
    resp = await client.patch(f"/v1/books/{seeded_books[0]}", json={"year": 2020})
    assert resp.status_code == 200
    assert resp.json()["year"] == 2020


async def test_patch_book_empty_body_returns_422(client, seeded_books) -> None:
    resp = await client.patch(f"/v1/books/{seeded_books[0]}", json={})
    assert resp.status_code == 422
    assert "At least one field" in str(resp.json()["details"])


async def test_patch_book_not_found(client) -> None:
    resp = await client.patch("/v1/books/999", json={"year": 2020})
    assert resp.status_code == 404


async def test_patch_status_field(client, seeded_books) -> None:
    resp = await client.patch(
        f"/v1/books/{seeded_books[0]}", json={"status": "archived"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


async def test_delete_book_success(client, seeded_books) -> None:
    resp = await client.delete(f"/v1/books/{seeded_books[0]}")
    assert resp.status_code == 204
    assert resp.content == b""
    follow = await client.get(f"/v1/books/{seeded_books[0]}")
    assert follow.status_code == 404


async def test_delete_book_not_found(client) -> None:
    resp = await client.delete("/v1/books/999")
    assert resp.status_code == 404
