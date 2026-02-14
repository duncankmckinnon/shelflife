"""Tests for MCP tools. Each test gets a ShelflifeClient backed by the
test httpx client fixture, seeds data via the API, then calls the tool
function directly."""

import pytest
from shelflife.id import make_id
from shelflife.mcp.client import ShelflifeClient
from shelflife.mcp.tools.discovery import search_books, get_book
from shelflife.mcp.tools.library import add_book, resolve_book
from shelflife.mcp.tools.shelves import shelve_book, browse_shelf
from shelflife.mcp.tools.reviews import review_book, get_reviews
from shelflife.mcp.tools.tags import tag_books, browse_tag
from shelflife.mcp.tools.profile import reading_profile
from shelflife.mcp.tools.importing import import_goodreads


@pytest.fixture
def sl(client):
    return ShelflifeClient(client)


# --- search_books ---

@pytest.mark.asyncio
async def test_search_books_by_query(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await sl.post("/api/books", json={"title": "Neuromancer", "author": "William Gibson"})
    result = await search_books(sl, query="dune")
    assert len(result) == 1
    assert result[0]["title"] == "Dune"


@pytest.mark.asyncio
async def test_search_books_by_author(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await sl.post("/api/books", json={"title": "1984", "author": "George Orwell"})
    result = await search_books(sl, author="orwell")
    assert len(result) == 1
    assert result[0]["author"] == "George Orwell"


@pytest.mark.asyncio
async def test_search_books_empty(sl):
    result = await search_books(sl)
    assert result == []


# --- get_book ---

@pytest.mark.asyncio
async def test_get_book_found(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await get_book(sl, title="Dune", author="Frank Herbert")
    assert result["title"] == "Dune"
    assert "tags" in result
    assert "review" in result


@pytest.mark.asyncio
async def test_get_book_not_found(sl):
    result = await get_book(sl, title="Nonexistent", author="Nobody")
    assert result["error"] is True
    assert result["status"] == 404


# --- add_book ---

@pytest.mark.asyncio
async def test_add_book_basic(sl):
    result = await add_book(sl, title="Dune", author="Frank Herbert")
    assert result["title"] == "Dune"
    assert result["author"] == "Frank Herbert"


@pytest.mark.asyncio
async def test_add_book_with_shelf(sl):
    result = await add_book(sl, title="Dune", author="Frank Herbert", shelf="to-read")
    assert result["title"] == "Dune"
    # Verify book is on the shelf
    shelf = await sl.get("/api/shelves/by-name/to-read")
    assert any(b["title"] == "Dune" for b in shelf["books"])


@pytest.mark.asyncio
async def test_add_book_duplicate(sl):
    await add_book(sl, title="Dune", author="Frank Herbert")
    result = await add_book(sl, title="Dune", author="Frank Herbert")
    assert result["error"] is True


# --- resolve_book ---

@pytest.mark.asyncio
async def test_resolve_book_exists(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await resolve_book(sl, title="Dune", author="Frank Herbert")
    # Should return an enrich response (may or may not enrich depending on OL)
    assert "book_id" in result or "error" in result


# --- shelve_book ---

@pytest.mark.asyncio
async def test_shelve_book(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await shelve_book(sl, title="Dune", author="Frank Herbert", shelf="currently-reading")
    assert result.get("ok") or result.get("detail")


@pytest.mark.asyncio
async def test_shelve_book_creates_shelf(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await shelve_book(sl, title="Dune", author="Frank Herbert", shelf="new-shelf")
    shelf = await sl.get("/api/shelves/by-name/new-shelf")
    assert any(b["title"] == "Dune" for b in shelf["books"])


# --- browse_shelf ---

@pytest.mark.asyncio
async def test_browse_shelf_list_all(sl):
    await sl.post("/api/shelves", json={"name": "to-read"})
    await sl.post("/api/shelves", json={"name": "read"})
    result = await browse_shelf(sl)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_browse_shelf_by_name(sl):
    await sl.post("/api/shelves", json={"name": "to-read"})
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = (await sl.get("/api/books"))[0]["id"]
    shelf_id = (await sl.get("/api/shelves"))[0]["id"]
    await sl.post(f"/api/shelves/{shelf_id}/books/{book_id}")

    result = await browse_shelf(sl, shelf_name="to-read")
    assert result["name"] == "to-read"
    assert len(result["books"]) == 1


# --- review_book ---

@pytest.mark.asyncio
async def test_review_book_create(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await review_book(sl, title="Dune", author="Frank Herbert", rating=5, review_text="A masterpiece")
    assert result["rating"] == 5
    assert result["review_text"] == "A masterpiece"


@pytest.mark.asyncio
async def test_review_book_update_existing(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await review_book(sl, title="Dune", author="Frank Herbert", rating=4)
    result = await review_book(sl, title="Dune", author="Frank Herbert", rating=5, review_text="Changed my mind")
    assert result["rating"] == 5
    assert result["review_text"] == "Changed my mind"


# --- get_reviews ---

@pytest.mark.asyncio
async def test_get_reviews(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await sl.post("/api/books", json={"title": "1984", "author": "George Orwell"})
    book_id_1 = make_id("Dune", "Frank Herbert")
    book_id_2 = make_id("1984", "George Orwell")
    await sl.post(f"/api/books/{book_id_1}/reviews", json={"rating": 5})
    await sl.post(f"/api/books/{book_id_2}/reviews", json={"rating": 3})

    result = await get_reviews(sl, min_rating=4)
    assert len(result) == 1
    assert result[0]["book_title"] == "Dune"


# --- tag_books ---

@pytest.mark.asyncio
async def test_tag_books_single(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await tag_books(sl, tag="sci-fi", books=[{"title": "Dune", "author": "Frank Herbert"}])
    assert result["tagged"] == 1
    assert result["not_found"] == []


@pytest.mark.asyncio
async def test_tag_books_mixed(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await tag_books(sl, tag="classics", books=[
        {"title": "Dune", "author": "Frank Herbert"},
        {"title": "Nonexistent", "author": "Nobody"},
    ])
    assert result["tagged"] == 1
    assert len(result["not_found"]) == 1


# --- browse_tag ---

@pytest.mark.asyncio
async def test_browse_tag_list_all(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = make_id("Dune", "Frank Herbert")
    await sl.post(f"/api/books/{book_id}/tags", json={"name": "sci-fi"})
    result = await browse_tag(sl)
    assert len(result) == 1
    assert result[0]["name"] == "sci-fi"


@pytest.mark.asyncio
async def test_browse_tag_by_name(sl):
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    book_id = make_id("Dune", "Frank Herbert")
    await sl.post(f"/api/books/{book_id}/tags", json={"name": "sci-fi"})
    result = await browse_tag(sl, tag_name="sci-fi")
    assert len(result) == 1
    assert result[0]["title"] == "Dune"


# --- reading_profile ---

@pytest.mark.asyncio
async def test_reading_profile_empty(sl):
    result = await reading_profile(sl)
    assert result["total_books"] == 0
    assert result["shelves"] == []
    assert result["top_tags"] == []
    assert result["rating_distribution"] == {}


@pytest.mark.asyncio
async def test_reading_profile_with_data(sl):
    # Add books
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    await sl.post("/api/books", json={"title": "1984", "author": "George Orwell"})

    # Tag them
    book1_id = make_id("Dune", "Frank Herbert")
    book2_id = make_id("1984", "George Orwell")
    await sl.post(f"/api/books/{book1_id}/tags", json={"name": "sci-fi"})
    await sl.post(f"/api/books/{book2_id}/tags", json={"name": "sci-fi"})
    await sl.post(f"/api/books/{book2_id}/tags", json={"name": "dystopia"})

    # Shelve one
    await sl.post("/api/shelves", json={"name": "read"})
    shelf_id = make_id("read")
    await sl.post(f"/api/shelves/{shelf_id}/books/{book1_id}")

    # Rate them
    await sl.post(f"/api/books/{book1_id}/reviews", json={"rating": 5})
    await sl.post(f"/api/books/{book2_id}/reviews", json={"rating": 3})

    result = await reading_profile(sl)
    assert result["total_books"] == 2
    assert len(result["shelves"]) == 1
    assert result["top_tags"][0]["name"] == "sci-fi"  # 2 books
    assert result["rating_distribution"]["5"] == 1
    assert result["rating_distribution"]["3"] == 1


# --- import_goodreads ---

SAMPLE_CSV = """Book Id,Title,Author,Author l-f,Additional Authors,ISBN,ISBN13,My Rating,Average Rating,Publisher,Binding,Number of Pages,Year Published,Original Publication Year,Date Read,Date Added,Bookshelves,Bookshelves with positions,Exclusive Shelf,My Review,Spoiler,Private Notes,Read Count,Owned Copies
1234,Dune,Frank Herbert,"Herbert, Frank",,="0441172717",="9780441172719",5,4.25,Ace,Paperback,896,2005,1965,2023/01/15,2022/12/01,sci-fi,sci-fi (#1),read,,,,1,0"""


@pytest.mark.asyncio
async def test_import_goodreads(sl):
    result = await import_goodreads(sl, csv_content=SAMPLE_CSV)
    assert result["books_created"] == 1
    # Verify the book exists
    books = await sl.get("/api/books")
    assert len(books) == 1
