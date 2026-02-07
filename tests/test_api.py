from unittest.mock import AsyncMock, patch

import pytest

from shelflife.services.openlibrary import OpenLibraryCandidate


@pytest.mark.asyncio
async def test_create_and_list_books(client):
    resp = await client.post("/api/books", json={
        "title": "Dune",
        "author": "Frank Herbert",
    })
    assert resp.status_code == 201
    book = resp.json()
    assert book["title"] == "Dune"
    book_id = book["id"]

    resp = await client.get("/api/books")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["id"] == book_id


@pytest.mark.asyncio
async def test_get_book_detail(client):
    resp = await client.post("/api/books", json={
        "title": "1984",
        "author": "George Orwell",
    })
    book_id = resp.json()["id"]

    resp = await client.get(f"/api/books/{book_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["title"] == "1984"
    assert detail["tags"] == []
    assert detail["review"] is None


@pytest.mark.asyncio
async def test_update_book(client):
    resp = await client.post("/api/books", json={"title": "Duen", "author": "Frank Herbert"})
    book_id = resp.json()["id"]

    resp = await client.put(f"/api/books/{book_id}", json={"title": "Dune"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dune"


@pytest.mark.asyncio
async def test_delete_book(client):
    resp = await client.post("/api/books", json={"title": "Temp", "author": "Nobody"})
    book_id = resp.json()["id"]

    resp = await client.delete(f"/api/books/{book_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/books/{book_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_shelves_crud(client):
    resp = await client.post("/api/shelves", json={"name": "Want to Read"})
    assert resp.status_code == 201
    shelf_id = resp.json()["id"]

    resp = await client.get("/api/shelves")
    assert len(resp.json()) == 1

    resp = await client.put(f"/api/shelves/{shelf_id}", json={"name": "To Read"})
    assert resp.json()["name"] == "To Read"


@pytest.mark.asyncio
async def test_add_book_to_shelf(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    shelf_resp = await client.post("/api/shelves", json={"name": "Read"})
    shelf_id = shelf_resp.json()["id"]

    resp = await client.post(f"/api/shelves/{shelf_id}/books/{book_id}")
    assert resp.status_code == 201

    # Verify book appears on shelf
    resp = await client.get(f"/api/shelves/{shelf_id}")
    assert len(resp.json()["books"]) == 1


@pytest.mark.asyncio
async def test_reviews_crud(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    resp = await client.post(f"/api/books/{book_id}/reviews", json={"rating": 5, "review_text": "Masterpiece"})
    assert resp.status_code == 201
    review_id = resp.json()["id"]

    resp = await client.get(f"/api/books/{book_id}/review")
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5

    resp = await client.put(f"/api/reviews/{review_id}", json={"rating": 4})
    assert resp.json()["rating"] == 4

    resp = await client.delete(f"/api/reviews/{review_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_tags(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    resp = await client.post(f"/api/books/{book_id}/tags", json={"name": "sci-fi"})
    assert resp.status_code == 201

    resp = await client.get("/api/tags")
    tags = resp.json()
    assert len(tags) == 1
    assert tags[0]["name"] == "sci-fi"
    tag_id = tags[0]["id"]

    resp = await client.delete(f"/api/books/{book_id}/tags/{tag_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_book_not_found(client):
    resp = await client.get("/api/books/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_books_by_title(client):
    await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await client.post("/api/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})
    await client.post("/api/books", json={"title": "1984", "author": "George Orwell"})

    resp = await client.get("/api/books/search", params={"title": "dune"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all("Dune" in b["title"] for b in results)

    resp = await client.get("/api/books/search", params={"title": "1984"})
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_quick_rating_creates_review(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    resp = await client.put(f"/api/books/{book_id}/rating", json={"rating": 5})
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5
    assert resp.json()["book_id"] == book_id

    # Verify review was created
    resp = await client.get(f"/api/books/{book_id}/review")
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5


@pytest.mark.asyncio
async def test_quick_rating_updates_existing(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    # Create review first
    await client.post(f"/api/books/{book_id}/reviews", json={"rating": 3, "review_text": "Good"})

    # Quick rate should update the existing review
    resp = await client.put(f"/api/books/{book_id}/rating", json={"rating": 5})
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5
    assert resp.json()["review_text"] == "Good"  # preserved

    # Still only one review
    resp = await client.get(f"/api/books/{book_id}/review")
    assert resp.status_code == 200
    assert resp.json()["rating"] == 5


@pytest.mark.asyncio
async def test_global_reviews_list(client):
    book1 = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book2 = await client.post("/api/books", json={"title": "1984", "author": "George Orwell"})

    await client.post(f"/api/books/{book1.json()['id']}/reviews", json={"rating": 5})
    await client.post(f"/api/books/{book2.json()['id']}/reviews", json={"rating": 3})

    resp = await client.get("/api/reviews")
    assert resp.status_code == 200
    reviews = resp.json()
    assert len(reviews) == 2
    # Should include book context
    assert all("book_title" in r and "book_author" in r for r in reviews)


@pytest.mark.asyncio
async def test_global_reviews_filter_by_rating(client):
    book1 = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book2 = await client.post("/api/books", json={"title": "1984", "author": "George Orwell"})

    await client.post(f"/api/books/{book1.json()['id']}/reviews", json={"rating": 5})
    await client.post(f"/api/books/{book2.json()['id']}/reviews", json={"rating": 3})

    resp = await client.get("/api/reviews", params={"min_rating": 4})
    assert len(resp.json()) == 1
    assert resp.json()[0]["rating"] == 5


@pytest.mark.asyncio
async def test_move_book_between_shelves(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    shelf1 = await client.post("/api/shelves", json={"name": "Currently Reading"})
    shelf1_id = shelf1.json()["id"]

    shelf2 = await client.post("/api/shelves", json={"name": "Read"})
    shelf2_id = shelf2.json()["id"]

    await client.post(f"/api/shelves/{shelf1_id}/books/{book_id}")

    resp = await client.post(f"/api/shelves/move-book/{book_id}", json={
        "from_shelf_id": shelf1_id,
        "to_shelf_id": shelf2_id,
    })
    assert resp.status_code == 200

    # Verify not on source shelf
    resp = await client.get(f"/api/shelves/{shelf1_id}")
    assert len(resp.json()["books"]) == 0

    # Verify on destination shelf
    resp = await client.get(f"/api/shelves/{shelf2_id}")
    assert len(resp.json()["books"]) == 1


@pytest.mark.asyncio
async def test_move_book_not_on_shelf(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    shelf1 = await client.post("/api/shelves", json={"name": "From"})
    shelf2 = await client.post("/api/shelves", json={"name": "To"})

    resp = await client.post(f"/api/shelves/move-book/{book_id}", json={
        "from_shelf_id": shelf1.json()["id"],
        "to_shelf_id": shelf2.json()["id"],
    })
    assert resp.status_code == 404
    assert "not on source shelf" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_books_by_tag(client):
    b1 = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    b2 = await client.post("/api/books", json={"title": "Neuromancer", "author": "William Gibson"})
    await client.post("/api/books", json={"title": "Pride and Prejudice", "author": "Jane Austen"})

    # Tag two books with "sci-fi"
    tag_resp = await client.post(f"/api/books/{b1.json()['id']}/tags", json={"name": "sci-fi"})
    tag_id = tag_resp.json()["id"]
    await client.post(f"/api/books/{b2.json()['id']}/tags", json={"name": "sci-fi"})

    # Get books by tag
    resp = await client.get(f"/api/tags/{tag_id}/books")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 2
    titles = {b["title"] for b in books}
    assert titles == {"Dune", "Neuromancer"}

    # 404 for nonexistent tag
    resp = await client.get("/api/tags/9999/books")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bulk_tag_book(client):
    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = book_resp.json()["id"]

    # Add multiple tags at once
    resp = await client.post(f"/api/books/{book_id}/tags/batch", json={
        "tags": ["sci-fi", "classic", "dystopian"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 3
    assert body["skipped"] == 0
    assert len(body["tags"]) == 3
    tag_names = {t["name"] for t in body["tags"]}
    assert tag_names == {"sci-fi", "classic", "dystopian"}

    # Repeat — should be idempotent
    resp = await client.post(f"/api/books/{book_id}/tags/batch", json={
        "tags": ["sci-fi", "classic", "dystopian"],
    })
    body = resp.json()
    assert body["created"] == 0
    assert body["skipped"] == 3

    # Mix of new and existing
    resp = await client.post(f"/api/books/{book_id}/tags/batch", json={
        "tags": ["sci-fi", "adventure"],
    })
    body = resp.json()
    assert body["created"] == 1
    assert body["skipped"] == 1

    # 404 for nonexistent book
    resp = await client.post("/api/books/9999/tags/batch", json={"tags": ["sci-fi"]})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bulk_tag_books(client):
    b1 = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    b2 = await client.post("/api/books", json={"title": "1984", "author": "George Orwell"})
    b3 = await client.post("/api/books", json={"title": "Neuromancer", "author": "William Gibson"})
    ids = [b1.json()["id"], b2.json()["id"], b3.json()["id"]]

    # Tag all three books with "sci-fi"
    resp = await client.post("/api/tags/books/batch", json={
        "tag": "sci-fi",
        "book_ids": ids,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["tag"]["name"] == "sci-fi"
    assert body["tagged"] == 3
    assert body["skipped"] == 0
    assert body["not_found"] == []

    # Repeat — idempotent
    resp = await client.post("/api/tags/books/batch", json={
        "tag": "sci-fi",
        "book_ids": ids,
    })
    body = resp.json()
    assert body["tagged"] == 0
    assert body["skipped"] == 3

    # Include a nonexistent book ID
    resp = await client.post("/api/tags/books/batch", json={
        "tag": "classic",
        "book_ids": [ids[0], 9999],
    })
    body = resp.json()
    assert body["tagged"] == 1
    assert body["not_found"] == [9999]


# --- Hash endpoint ---


@pytest.mark.asyncio
async def test_hash_endpoint(client):
    resp = await client.get("/api/hash", params={"parts": "sci-fi"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["parts"] == ["sci-fi"]
    assert isinstance(body["id"], int)

    # Multiple parts
    resp = await client.get("/api/hash", params={"parts": ["Dune", "Frank Herbert"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["parts"] == ["Dune", "Frank Herbert"]
    assert isinstance(body["id"], int)


@pytest.mark.asyncio
async def test_hash_matches_created_ids(client):
    # Hash endpoint should return the same ID as the created entity
    resp = await client.get("/api/hash", params={"parts": ["Dune", "Frank Herbert"]})
    expected_id = resp.json()["id"]

    book_resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert book_resp.json()["id"] == expected_id

    resp = await client.get("/api/hash", params={"parts": "sci-fi"})
    expected_tag_id = resp.json()["id"]

    tag_resp = await client.post(f"/api/books/{expected_id}/tags", json={"name": "sci-fi"})
    assert tag_resp.json()["id"] == expected_tag_id


# --- By-name endpoints ---


@pytest.mark.asyncio
async def test_get_book_by_name(client):
    resp = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert resp.status_code == 201
    book_id = resp.json()["id"]

    resp = await client.get("/api/books/by-name/Dune/Frank Herbert")
    assert resp.status_code == 200
    assert resp.json()["id"] == book_id
    assert resp.json()["title"] == "Dune"


@pytest.mark.asyncio
async def test_get_book_by_name_not_found(client):
    resp = await client.get("/api/books/by-name/Nonexistent/Nobody")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_books_by_tag_name(client):
    b1 = await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    b2 = await client.post("/api/books", json={"title": "Neuromancer", "author": "William Gibson"})

    await client.post(f"/api/books/{b1.json()['id']}/tags", json={"name": "sci-fi"})
    await client.post(f"/api/books/{b2.json()['id']}/tags", json={"name": "sci-fi"})

    resp = await client.get("/api/tags/by-name/sci-fi/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    titles = {b["title"] for b in resp.json()}
    assert titles == {"Dune", "Neuromancer"}


@pytest.mark.asyncio
async def test_get_books_by_tag_name_not_found(client):
    resp = await client.get("/api/tags/by-name/nonexistent/books")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_shelf_by_name(client):
    resp = await client.post("/api/shelves", json={"name": "Want to Read"})
    assert resp.status_code == 201
    shelf_id = resp.json()["id"]

    resp = await client.get("/api/shelves/by-name/Want to Read")
    assert resp.status_code == 200
    assert resp.json()["id"] == shelf_id
    assert resp.json()["name"] == "Want to Read"


@pytest.mark.asyncio
async def test_get_shelf_by_name_not_found(client):
    resp = await client.get("/api/shelves/by-name/Nonexistent")
    assert resp.status_code == 404


# --- Lookup and resolve endpoints ---


MOCK_CANDIDATES = [
    OpenLibraryCandidate(
        title="Dune",
        author="Frank Herbert",
        open_library_key="/works/OL893415W",
        cover_url="https://covers.openlibrary.org/b/id/12345-L.jpg",
        isbn="0441172717",
        isbn13="9780441172719",
        publisher="Ace Books",
        year_published=1965,
        page_count=412,
    ),
    OpenLibraryCandidate(
        title="Dune Messiah",
        author="Frank Herbert",
        open_library_key="/works/OL893416W",
        cover_url=None,
        isbn=None,
        isbn13=None,
        publisher="Putnam",
        year_published=1969,
        page_count=256,
    ),
]


@pytest.mark.asyncio
async def test_lookup_book(client):
    with patch(
        "shelflife.routers.books.search_candidates",
        new_callable=AsyncMock,
        return_value=MOCK_CANDIDATES,
    ):
        resp = await client.get("/api/books/lookup", params={"title": "Dune", "author": "Frank Herbert"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert results[0]["title"] == "Dune"
    assert results[0]["isbn"] == "0441172717"
    assert results[1]["title"] == "Dune Messiah"


@pytest.mark.asyncio
async def test_lookup_book_no_results(client):
    with patch(
        "shelflife.routers.books.search_candidates",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.get("/api/books/lookup", params={"title": "xyznonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_book_with_resolve(client):
    with patch(
        "shelflife.routers.books.search_candidates",
        new_callable=AsyncMock,
        return_value=[MOCK_CANDIDATES[0]],
    ):
        resp = await client.post(
            "/api/books?resolve=true",
            json={"title": "dune", "author": "herbert"},
        )
    assert resp.status_code == 201
    book = resp.json()
    # Should use canonical title/author from Open Library
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    # Should fill in metadata from candidate
    assert book["isbn"] == "0441172717"
    assert book["isbn13"] == "9780441172719"
    assert book["publisher"] == "Ace Books"
    assert book["year_published"] == 1965
    assert book["page_count"] == 412


@pytest.mark.asyncio
async def test_create_book_with_resolve_no_match(client):
    with patch(
        "shelflife.routers.books.search_candidates",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.post(
            "/api/books?resolve=true",
            json={"title": "My Unpublished Novel", "author": "Me"},
        )
    assert resp.status_code == 201
    book = resp.json()
    # Falls back to provided values
    assert book["title"] == "My Unpublished Novel"
    assert book["author"] == "Me"


@pytest.mark.asyncio
async def test_create_book_resolve_preserves_provided_fields(client):
    with patch(
        "shelflife.routers.books.search_candidates",
        new_callable=AsyncMock,
        return_value=[MOCK_CANDIDATES[0]],
    ):
        resp = await client.post(
            "/api/books?resolve=true",
            json={"title": "dune", "author": "herbert", "publisher": "My Edition"},
        )
    assert resp.status_code == 201
    book = resp.json()
    # Canonical title/author from resolve
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    # Provided publisher should NOT be overwritten
    assert book["publisher"] == "My Edition"
    # But missing fields should be filled
    assert book["isbn"] == "0441172717"
