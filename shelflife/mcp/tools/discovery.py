from shelflife.mcp.client import ShelflifeClient


async def search_books(
    client: ShelflifeClient,
    query: str | None = None,
    author: str | None = None,
    tag: str | None = None,
    started_after: str | None = None,
    started_before: str | None = None,
    finished_after: str | None = None,
    finished_before: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    params = {"limit": limit, "offset": offset}
    if query:
        params["q"] = query
    if author:
        params["author"] = author
    if tag:
        params["tag"] = tag
    if started_after:
        params["started_after"] = started_after
    if started_before:
        params["started_before"] = started_before
    if finished_after:
        params["finished_after"] = finished_after
    if finished_before:
        params["finished_before"] = finished_before
    result = await client.get("/api/books", params=params)
    if isinstance(result, dict) and result.get("error"):
        return []
    return result


async def get_book(
    client: ShelflifeClient,
    title: str,
    author: str,
) -> dict:
    return await client.get(f"/api/books/by-name/{title}/{author}")
