import pytest


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
    assert detail["reviews"] == []


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

    resp = await client.get(f"/api/books/{book_id}/reviews")
    assert len(resp.json()) == 1

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
    resp = await client.get(f"/api/books/{book_id}/reviews")
    assert len(resp.json()) == 1
    assert resp.json()[0]["rating"] == 5


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
    resp = await client.get(f"/api/books/{book_id}/reviews")
    assert len(resp.json()) == 1


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
