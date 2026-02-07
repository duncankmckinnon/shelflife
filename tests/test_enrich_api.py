"""Tests for enrichment API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from shelflife.services.openlibrary import OpenLibraryMetadata


@pytest.fixture
def mock_metadata():
    return OpenLibraryMetadata(
        open_library_key="/works/OL893415W",
        description="Set on the desert planet Arrakis...",
        cover_url="https://covers.openlibrary.org/b/isbn/0441172717-L.jpg",
        page_count=688,
        publisher="Ace Books",
        publish_year=2005,
        subjects=["science fiction", "adventure"],
    )


async def test_enrich_book_endpoint(client, mock_metadata):
    resp = await client.post("/api/books", json={
        "title": "Dune", "author": "Frank Herbert", "isbn": "0441172717",
    })
    book_id = resp.json()["id"]

    with patch("shelflife.services.enrich_service.fetch_metadata", new_callable=AsyncMock, return_value=mock_metadata):
        resp = await client.post(f"/api/books/{book_id}/enrich")

    assert resp.status_code == 200
    data = resp.json()
    assert data["enriched"] is True
    assert "description" in data["fields_updated"]
    assert "cover_url" in data["fields_updated"]
    assert "science fiction" in data["tags_added"]

    # Verify book was updated
    resp = await client.get(f"/api/books/{book_id}")
    book = resp.json()
    assert book["description"] == "Set on the desert planet Arrakis..."
    assert book["open_library_key"] == "/works/OL893415W"


async def test_enrich_book_not_found(client):
    resp = await client.post("/api/books/9999/enrich")
    assert resp.status_code == 404


async def test_enrich_no_overwrite(client, mock_metadata):
    """Enrichment should not overwrite existing fields by default."""
    resp = await client.post("/api/books", json={
        "title": "Dune", "author": "Frank Herbert",
        "description": "My custom description",
    })
    book_id = resp.json()["id"]

    with patch("shelflife.services.enrich_service.fetch_metadata", new_callable=AsyncMock, return_value=mock_metadata):
        resp = await client.post(f"/api/books/{book_id}/enrich")

    assert resp.status_code == 200
    # description should NOT have been overwritten
    assert "description" not in resp.json()["fields_updated"]

    resp = await client.get(f"/api/books/{book_id}")
    assert resp.json()["description"] == "My custom description"


async def test_enrich_with_overwrite(client, mock_metadata):
    resp = await client.post("/api/books", json={
        "title": "Dune", "author": "Frank Herbert",
        "description": "My custom description",
    })
    book_id = resp.json()["id"]

    with patch("shelflife.services.enrich_service.fetch_metadata", new_callable=AsyncMock, return_value=mock_metadata):
        resp = await client.post(f"/api/books/{book_id}/enrich?overwrite=true")

    assert resp.status_code == 200
    assert "description" in resp.json()["fields_updated"]

    resp = await client.get(f"/api/books/{book_id}")
    assert resp.json()["description"] == "Set on the desert planet Arrakis..."


async def test_enrich_graceful_failure(client):
    """When Open Library returns nothing, should not error."""
    resp = await client.post("/api/books", json={
        "title": "Unknown Book", "author": "Nobody",
    })
    book_id = resp.json()["id"]

    with patch("shelflife.services.enrich_service.fetch_metadata", new_callable=AsyncMock, return_value=None):
        resp = await client.post(f"/api/books/{book_id}/enrich")

    assert resp.status_code == 200
    data = resp.json()
    assert data["enriched"] is False
    assert data["error"] == "No metadata found"


async def test_create_book_with_enrich(client, mock_metadata):
    with patch("shelflife.services.enrich_service.fetch_metadata", new_callable=AsyncMock, return_value=mock_metadata):
        resp = await client.post("/api/books?enrich=true", json={
            "title": "Dune", "author": "Frank Herbert", "isbn": "0441172717",
        })

    assert resp.status_code == 201
    book = resp.json()
    assert book["description"] == "Set on the desert planet Arrakis..."
    assert book["open_library_key"] == "/works/OL893415W"


async def test_batch_enrich(client, mock_metadata):
    # Create two books
    await client.post("/api/books", json={"title": "Book A", "author": "Author A"})
    await client.post("/api/books", json={"title": "Book B", "author": "Author B"})

    with patch("shelflife.services.enrich_service.fetch_metadata", new_callable=AsyncMock, return_value=mock_metadata):
        resp = await client.post("/api/import/enrich", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["enriched"] == 2
