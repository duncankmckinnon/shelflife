"""Tests for reading tracking endpoints."""

import pytest
from datetime import date


# --- helpers ---

async def _create_book(client, title="Dune", author="Frank Herbert"):
    resp = await client.post("/api/books", json={"title": title, "author": author})
    assert resp.status_code == 201
    return resp.json()


# --- start reading ---

@pytest.mark.asyncio
async def test_start_reading(client):
    book = await _create_book(client)
    resp = await client.post(f"/api/books/{book['id']}/start-reading")
    assert resp.status_code == 201
    data = resp.json()
    assert data["book_id"] == book["id"]
    assert data["started_at"] == date.today().isoformat()
    assert data["finished_at"] is None


@pytest.mark.asyncio
async def test_start_reading_custom_date(client):
    book = await _create_book(client)
    resp = await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-01-15"},
    )
    assert resp.status_code == 201
    assert resp.json()["started_at"] == "2025-01-15"


@pytest.mark.asyncio
async def test_start_reading_book_not_found(client):
    resp = await client.post("/api/books/999999/start-reading")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_reading_duplicate(client):
    book = await _create_book(client)
    resp1 = await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-01-15"},
    )
    assert resp1.status_code == 201
    resp2 = await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-01-15"},
    )
    assert resp2.status_code == 409


# --- finish reading ---

@pytest.mark.asyncio
async def test_finish_reading(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    resp = await client.put(f"/api/books/{book['id']}/finish-reading")
    assert resp.status_code == 200
    data = resp.json()
    assert data["finished_at"] == date.today().isoformat()
    assert data["duration_days"] == 0  # started and finished today


@pytest.mark.asyncio
async def test_finish_reading_with_duration(client):
    book = await _create_book(client)
    await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-01-01"},
    )
    resp = await client.put(
        f"/api/books/{book['id']}/finish-reading",
        json={"finished_at": "2025-01-15"},
    )
    assert resp.status_code == 200
    assert resp.json()["duration_days"] == 14


@pytest.mark.asyncio
async def test_finish_reading_no_active(client):
    book = await _create_book(client)
    resp = await client.put(f"/api/books/{book['id']}/finish-reading")
    assert resp.status_code == 404


# --- list readings ---

@pytest.mark.asyncio
async def test_list_readings(client):
    book = await _create_book(client)
    await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-01-01"},
    )
    await client.put(
        f"/api/books/{book['id']}/finish-reading",
        json={"finished_at": "2025-01-15"},
    )
    # Start a re-read
    await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-06-01"},
    )

    resp = await client.get(f"/api/books/{book['id']}/readings")
    assert resp.status_code == 200
    readings = resp.json()
    assert len(readings) == 2


# --- get reading detail ---

@pytest.mark.asyncio
async def test_get_reading_detail(client):
    book = await _create_book(client)
    start_resp = await client.post(f"/api/books/{book['id']}/start-reading")
    reading_id = start_resp.json()["id"]
    resp = await client.get(f"/api/books/{book['id']}/readings/{reading_id}")
    assert resp.status_code == 200
    assert resp.json()["progress_entries"] == []


# --- update reading ---

@pytest.mark.asyncio
async def test_update_reading(client):
    book = await _create_book(client)
    start_resp = await client.post(
        f"/api/books/{book['id']}/start-reading",
        json={"started_at": "2025-01-01"},
    )
    reading_id = start_resp.json()["id"]
    resp = await client.put(
        f"/api/books/{book['id']}/readings/{reading_id}",
        json={"started_at": "2024-12-25"},
    )
    assert resp.status_code == 200
    assert resp.json()["started_at"] == "2024-12-25"


# --- delete reading ---

@pytest.mark.asyncio
async def test_delete_reading(client):
    book = await _create_book(client)
    start_resp = await client.post(f"/api/books/{book['id']}/start-reading")
    reading_id = start_resp.json()["id"]
    resp = await client.delete(f"/api/books/{book['id']}/readings/{reading_id}")
    assert resp.status_code == 204

    readings = await client.get(f"/api/books/{book['id']}/readings")
    assert len(readings.json()) == 0


# --- log progress ---

@pytest.mark.asyncio
async def test_log_progress_absolute_page(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 50},
    )
    assert resp.status_code == 201
    assert resp.json()["page"] == 50


@pytest.mark.asyncio
async def test_log_progress_pages_read(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    # First entry at page 50
    await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 50, "date": "2025-01-01"},
    )
    # Read 30 more pages
    resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"pages_read": 30, "date": "2025-01-02"},
    )
    assert resp.status_code == 201
    assert resp.json()["page"] == 80


@pytest.mark.asyncio
async def test_log_progress_page_range(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"start_page": 100, "end_page": 150},
    )
    assert resp.status_code == 201
    assert resp.json()["page"] == 150


@pytest.mark.asyncio
async def test_log_progress_no_active_reading(client):
    book = await _create_book(client)
    resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 50},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_log_progress_validation_no_input(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_log_progress_validation_multiple_inputs(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 50, "pages_read": 30},
    )
    assert resp.status_code == 422


# --- get active progress ---

@pytest.mark.asyncio
async def test_get_active_progress(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 50, "date": "2025-01-01"},
    )
    await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 100, "date": "2025-01-02"},
    )
    resp = await client.get(f"/api/books/{book['id']}/reading/progress")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 2
    assert entries[0]["page"] == 50
    assert entries[1]["page"] == 100


# --- delete progress ---

@pytest.mark.asyncio
async def test_delete_progress(client):
    book = await _create_book(client)
    await client.post(f"/api/books/{book['id']}/start-reading")
    progress_resp = await client.post(
        f"/api/books/{book['id']}/reading/progress",
        json={"page": 50},
    )
    progress_id = progress_resp.json()["id"]
    resp = await client.delete(f"/api/reading/progress/{progress_id}")
    assert resp.status_code == 204
