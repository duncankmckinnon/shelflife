from shelflife.mcp.client import ShelflifeClient


async def search_books(
    client: ShelflifeClient,
    query: str | None = None,
    author: str | None = None,
    tag: str | None = None,
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
