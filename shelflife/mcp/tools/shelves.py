from shelflife.id import make_id
from shelflife.mcp.client import ShelflifeClient


EXCLUSIVE_SHELF_NAMES = {"read", "currently-reading", "to-read"}


async def shelve_book(
    client: ShelflifeClient,
    title: str,
    author: str,
    shelf: str,
) -> dict:
    book_id = make_id(title, author)
    shelf_id = make_id(shelf)

    # Create shelf if it doesn't exist
    shelf_resp = await client.get(f"/api/shelves/{shelf_id}")
    if isinstance(shelf_resp, dict) and shelf_resp.get("error"):
        is_exclusive = shelf.lower() in EXCLUSIVE_SHELF_NAMES
        await client.post("/api/shelves", json={"name": shelf, "is_exclusive": is_exclusive})

    return await client.post(f"/api/shelves/{shelf_id}/books/{book_id}")


async def browse_shelf(
    client: ShelflifeClient,
    shelf_name: str | None = None,
) -> dict | list:
    if shelf_name:
        return await client.get(f"/api/shelves/by-name/{shelf_name}")
    return await client.get("/api/shelves")
