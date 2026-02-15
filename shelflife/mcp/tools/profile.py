from collections import Counter

from shelflife.mcp.client import ShelflifeClient


async def _fetch_all_reviews(client: ShelflifeClient) -> list[dict]:
    """Paginate through all reviews (API caps at 200 per request)."""
    all_reviews: list[dict] = []
    offset = 0
    while True:
        batch = await client.get("/api/reviews", params={"limit": 200, "offset": offset})
        if isinstance(batch, dict) and batch.get("error"):
            break
        if not batch:
            break
        all_reviews.extend(batch)
        if len(batch) < 200:
            break
        offset += 200
    return all_reviews


async def reading_profile(client: ShelflifeClient) -> dict:
    stats = await client.get("/api/books/stats")
    total_books = stats.get("total_books", 0) if isinstance(stats, dict) else 0

    # Recent books (most recently added)
    recent = await client.get("/api/books", params={"limit": 5, "sort": "created_at", "order": "desc"})
    if isinstance(recent, dict) and recent.get("error"):
        recent = []

    shelves = await client.get("/api/shelves")
    if isinstance(shelves, dict) and shelves.get("error"):
        shelves = []

    tags = await client.get("/api/tags")
    if isinstance(tags, dict) and tags.get("error"):
        tags = []

    reviews = await _fetch_all_reviews(client)

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
        "total_books": total_books,
        "total_reviews": len(reviews),
        "shelves": shelf_summaries,
        "top_tags": tag_counts[:10],
        "rating_distribution": dict(rating_dist),
        "recent_books": [
            {"title": b["title"], "author": b["author"]}
            for b in recent[:5]
        ],
    }
