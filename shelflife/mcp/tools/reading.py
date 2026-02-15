from datetime import date

from shelflife.id import make_id
from shelflife.mcp.client import ShelflifeClient


async def start_reading(
    client: ShelflifeClient,
    title: str,
    author: str,
    started_at: str | None = None,
) -> dict:
    book_id = make_id(title, author)
    body = {}
    if started_at is not None:
        body["started_at"] = started_at
    return await client.post(f"/api/books/{book_id}/start-reading", json=body)


async def finish_reading(
    client: ShelflifeClient,
    title: str,
    author: str,
    finished_at: str | None = None,
) -> dict:
    book_id = make_id(title, author)
    body = {}
    if finished_at is not None:
        body["finished_at"] = finished_at
    return await client.put(f"/api/books/{book_id}/finish-reading", json=body)


async def log_reading_progress(
    client: ShelflifeClient,
    title: str,
    author: str,
    page: int | None = None,
    pages_read: int | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
    progress_date: str | None = None,
) -> dict:
    book_id = make_id(title, author)
    body = {}
    if page is not None:
        body["page"] = page
    if pages_read is not None:
        body["pages_read"] = pages_read
    if start_page is not None:
        body["start_page"] = start_page
    if end_page is not None:
        body["end_page"] = end_page
    if progress_date is not None:
        body["date"] = progress_date
    return await client.post(f"/api/books/{book_id}/reading/progress", json=body)


async def get_reading_history(
    client: ShelflifeClient,
    title: str,
    author: str,
) -> list[dict]:
    book_id = make_id(title, author)
    result = await client.get(f"/api/books/{book_id}/readings")
    if isinstance(result, dict) and result.get("error"):
        return []
    return result
