import pytest
from shelflife.mcp.client import ShelflifeClient


@pytest.mark.asyncio
async def test_client_get_success(client):
    """Client.get returns parsed JSON for a successful response."""
    await client.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})

    sl = ShelflifeClient(client)
    result = await sl.get("/api/books")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Dune"


@pytest.mark.asyncio
async def test_client_get_404(client):
    """Client.get returns error dict for 404."""
    sl = ShelflifeClient(client)
    result = await sl.get("/api/books/999")
    assert result["error"] is True
    assert result["status"] == 404


@pytest.mark.asyncio
async def test_client_post_success(client):
    """Client.post returns parsed JSON for 201."""
    sl = ShelflifeClient(client)
    result = await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert result["title"] == "Dune"
    assert result["author"] == "Frank Herbert"


@pytest.mark.asyncio
async def test_client_post_409(client):
    """Client.post returns error dict for 409 conflict."""
    sl = ShelflifeClient(client)
    await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    result = await sl.post("/api/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert result["error"] is True
    assert result["status"] == 409
