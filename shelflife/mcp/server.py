from fastmcp import FastMCP

from shelflife.mcp.client import ShelflifeClient
from shelflife.mcp.tools.discovery import search_books as _search_books, get_book as _get_book
from shelflife.mcp.tools.library import add_book as _add_book, resolve_book as _resolve_book
from shelflife.mcp.tools.shelves import shelve_book as _shelve_book, browse_shelf as _browse_shelf
from shelflife.mcp.tools.reviews import review_book as _review_book, get_reviews as _get_reviews
from shelflife.mcp.tools.tags import tag_books as _tag_books, browse_tag as _browse_tag
from shelflife.mcp.tools.profile import reading_profile as _reading_profile
from shelflife.mcp.tools.importing import import_goodreads as _import_goodreads


def create_mcp_server(client: ShelflifeClient) -> FastMCP:
    mcp = FastMCP(
        name="shelflife",
        instructions=(
            "Shelflife is a personal reading library manager. Use these tools to "
            "search books, manage shelves, write reviews, tag books by topic, and "
            "understand reading interests. Books are identified by title and author."
        ),
    )

    @mcp.tool()
    async def search_books(
        query: str | None = None,
        author: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search your book library by title, author, tag, or free text query."""
        return await _search_books(client, query=query, author=author, tag=tag, limit=limit)

    @mcp.tool()
    async def get_book(title: str, author: str) -> dict:
        """Get full details for a book including tags, shelves, and review."""
        return await _get_book(client, title=title, author=author)

    @mcp.tool()
    async def add_book(title: str, author: str, shelf: str | None = None) -> dict:
        """Add a book to the library. Resolves against Open Library for canonical
        metadata, enriches with description/cover/subject tags. Optionally place
        on a shelf (created if it doesn't exist)."""
        return await _add_book(client, title=title, author=author, shelf=shelf)

    @mcp.tool()
    async def resolve_book(title: str, author: str) -> dict:
        """Enrich an existing book by matching it against Open Library for
        metadata, cover art, and subject tags."""
        return await _resolve_book(client, title=title, author=author)

    @mcp.tool()
    async def shelve_book(title: str, author: str, shelf: str) -> dict:
        """Put a book on a shelf (e.g. 'to-read', 'currently-reading', 'read').
        Creates the shelf if it doesn't exist."""
        return await _shelve_book(client, title=title, author=author, shelf=shelf)

    @mcp.tool()
    async def browse_shelf(shelf_name: str | None = None) -> dict | list:
        """List all shelves (no argument) or get books on a specific shelf."""
        return await _browse_shelf(client, shelf_name=shelf_name)

    @mcp.tool()
    async def review_book(
        title: str,
        author: str,
        rating: int | None = None,
        review_text: str | None = None,
    ) -> dict:
        """Rate and/or review a book. Creates a new review or updates existing one.
        Rating is 1-5."""
        return await _review_book(client, title=title, author=author, rating=rating, review_text=review_text)

    @mcp.tool()
    async def get_reviews(min_rating: int | None = None, limit: int = 50) -> list[dict]:
        """List book reviews, optionally filtered by minimum rating."""
        return await _get_reviews(client, min_rating=min_rating, limit=limit)

    @mcp.tool()
    async def tag_books(tag: str, books: list[dict]) -> dict:
        """Apply a tag to one or more books. Each book in the list needs
        'title' and 'author' fields. Reports which books were tagged and
        which were not found."""
        return await _tag_books(client, tag=tag, books=books)

    @mcp.tool()
    async def browse_tag(tag_name: str | None = None) -> list[dict]:
        """List all tags (no argument) or get books with a specific tag."""
        return await _browse_tag(client, tag_name=tag_name)

    @mcp.tool()
    async def reading_profile() -> dict:
        """Get an overview of reading interests: total books, shelves,
        top tags, rating distribution, and recently added books."""
        return await _reading_profile(client)

    @mcp.tool()
    async def import_goodreads(csv_content: str) -> dict:
        """Import a Goodreads library export (CSV content as a string).
        Creates books, shelves, reviews from the export data."""
        return await _import_goodreads(client, csv_content=csv_content)

    return mcp
