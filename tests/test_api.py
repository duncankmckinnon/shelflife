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
