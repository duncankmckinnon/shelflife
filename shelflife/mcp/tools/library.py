from shelflife.id import make_id
from shelflife.mcp.client import ShelflifeClient


async def add_book(
    client: ShelflifeClient,
    title: str,
    author: str,
    shelf: str | None = None,
) -> dict:
    result = await client.post(
        "/api/books",
        params={"resolve": "true", "enrich": "true"},
        json={"title": title, "author": author},
    )
    if isinstance(result, dict) and result.get("error"):
        return result

    book_id = result["id"]

    if shelf:
        me = await client.get("/api/auth/me")
        shelf_id = make_id(me["user_id"], shelf)
        # Create shelf if it doesn't exist
        shelf_resp = await client.get(f"/api/shelves/{shelf_id}")
        if isinstance(shelf_resp, dict) and shelf_resp.get("error"):
            await client.post("/api/shelves", json={"name": shelf})
        await client.post(f"/api/shelves/{shelf_id}/books/{book_id}")

    return result


async def resolve_book(
    client: ShelflifeClient,
    title: str,
    author: str,
) -> dict:
    book_id = make_id(title, author)
    return await client.post(f"/api/books/{book_id}/enrich")
