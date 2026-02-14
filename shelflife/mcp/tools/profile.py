from collections import Counter

from shelflife.mcp.client import ShelflifeClient


async def reading_profile(client: ShelflifeClient) -> dict:
    books = await client.get("/api/books", params={"limit": 200})
    if isinstance(books, dict) and books.get("error"):
        books = []

    shelves = await client.get("/api/shelves")
    if isinstance(shelves, dict) and shelves.get("error"):
        shelves = []

    tags = await client.get("/api/tags")
    if isinstance(tags, dict) and tags.get("error"):
        tags = []

    reviews = await client.get("/api/reviews", params={"limit": 200})
    if isinstance(reviews, dict) and reviews.get("error"):
        reviews = []

    # Rating distribution
    rating_dist = Counter()
    for r in reviews:
        if r.get("rating"):
            rating_dist[str(r["rating"])] += 1

    # Count books per tag
    tag_counts = []
    for t in tags:
        tag_books = await client.get(f"/api/tags/{t['id']}/books")
        if isinstance(tag_books, list):
            tag_counts.append({"name": t["name"], "count": len(tag_books)})
    tag_counts.sort(key=lambda x: x["count"], reverse=True)

    # Shelf summaries
    shelf_summaries = [{"name": s["name"], "id": s["id"]} for s in shelves]

    return {
        "total_books": len(books),
        "shelves": shelf_summaries,
        "top_tags": tag_counts[:10],
        "rating_distribution": dict(rating_dist),
        "recent_books": [
            {"title": b["title"], "author": b["author"]}
            for b in sorted(books, key=lambda x: x["created_at"], reverse=True)[:5]
        ],
    }
