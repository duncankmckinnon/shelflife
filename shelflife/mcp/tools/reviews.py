from shelflife.id import make_id
from shelflife.mcp.client import ShelflifeClient


async def review_book(
    client: ShelflifeClient,
    title: str,
    author: str,
    rating: int | None = None,
    review_text: str | None = None,
) -> dict:
    book_id = make_id(title, author)

    body = {}
    if rating is not None:
        body["rating"] = rating
    if review_text is not None:
        body["review_text"] = review_text

    # Try to create a new review
    result = await client.post(f"/api/books/{book_id}/reviews", json=body)

    # If 409 (already exists), update instead
    if isinstance(result, dict) and result.get("status") == 409:
        review_id = make_id(book_id)
        result = await client.put(f"/api/reviews/{review_id}", json=body)

    return result


async def get_reviews(
    client: ShelflifeClient,
    min_rating: int | None = None,
    limit: int = 50,
) -> list[dict]:
    params = {"limit": limit}
    if min_rating is not None:
        params["min_rating"] = min_rating
    result = await client.get("/api/reviews", params=params)
    if isinstance(result, dict) and result.get("error"):
        return []
    return result
