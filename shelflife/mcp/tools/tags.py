from shelflife.id import make_id
from shelflife.mcp.client import ShelflifeClient


async def tag_books(
    client: ShelflifeClient,
    tag: str,
    books: list[dict],
) -> dict:
    book_ids = [make_id(b["title"], b["author"]) for b in books]
    result = await client.post("/api/tags/books/batch", json={"tag": tag, "book_ids": book_ids})

    # Translate not_found IDs back to title/author for readability
    if isinstance(result, dict) and "not_found" in result:
        not_found_ids = set(result["not_found"])
        result["not_found"] = [
            f"{b['title']} by {b['author']}"
            for b, bid in zip(books, book_ids)
            if bid in not_found_ids
        ]

    return result


async def browse_tag(
    client: ShelflifeClient,
    tag_name: str | None = None,
) -> list[dict]:
    if tag_name:
        result = await client.get(f"/api/tags/by-name/{tag_name}/books")
        if isinstance(result, dict) and result.get("error"):
            return []
        return result
    result = await client.get("/api/tags")
    if isinstance(result, dict) and result.get("error"):
        return []
    return result
