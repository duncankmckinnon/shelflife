"""Tests for the Open Library API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from shelflife.services.openlibrary import (
    _extract_year,
    _pick_best_match,
    fetch_metadata,
    fetch_metadata_by_isbn,
    fetch_metadata_by_title_author,
)


def test_extract_year_full_date():
    assert _extract_year("March 1, 2004") == 2004


def test_extract_year_plain():
    assert _extract_year("1965") == 1965


def test_extract_year_none():
    assert _extract_year(None) is None


def test_extract_year_empty():
    assert _extract_year("") is None


def test_extract_year_no_match():
    assert _extract_year("Unknown") is None


def test_pick_best_match_exact_title():
    docs = [
        {"title": "Dune Messiah", "author_name": ["Frank Herbert"], "key": "OL2"},
        {"title": "Dune", "author_name": ["Frank Herbert"], "key": "OL1", "cover_i": 123},
    ]
    best = _pick_best_match(docs, "Dune", "Frank Herbert")
    assert best["key"] == "OL1"


def test_pick_best_match_partial_title():
    docs = [
        {"title": "The Complete Dune Saga", "author_name": ["Frank Herbert"], "key": "OL1"},
    ]
    best = _pick_best_match(docs, "Dune", "Frank Herbert")
    assert best["key"] == "OL1"


def test_pick_best_match_no_match():
    docs = [
        {"title": "Completely Different Book", "author_name": ["Other Author"], "key": "OL1"},
    ]
    best = _pick_best_match(docs, "Dune", "Frank Herbert")
    assert best is None


def test_pick_best_match_empty():
    assert _pick_best_match([], "Dune", "Frank Herbert") is None


def _mock_response(status_code, json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


@pytest.fixture
def mock_isbn_responses():
    """Edition + work responses for ISBN lookup."""
    edition = {
        "number_of_pages": 688,
        "publishers": ["Ace Books"],
        "publish_date": "2005",
        "works": [{"key": "/works/OL893415W"}],
    }
    work = {
        "description": "Set on the desert planet Arrakis...",
        "subjects": ["Science Fiction", "Adventure"],
    }
    return edition, work


@pytest.mark.asyncio
async def test_fetch_metadata_by_isbn_success(mock_isbn_responses):
    edition, work = mock_isbn_responses

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[_mock_response(200, edition), _mock_response(200, work)]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata_by_isbn("0441172717")

    assert result is not None
    assert result.open_library_key == "/works/OL893415W"
    assert result.description == "Set on the desert planet Arrakis..."
    assert result.page_count == 688
    assert result.publisher == "Ace Books"
    assert result.publish_year == 2005
    assert "Science Fiction" in result.subjects


@pytest.mark.asyncio
async def test_fetch_metadata_by_isbn_not_found():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response(404, {}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata_by_isbn("0000000000")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_metadata_by_isbn_network_error():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata_by_isbn("0441172717")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_metadata_by_isbn_description_as_dict():
    """Open Library sometimes returns description as a dict."""
    edition = {"works": [{"key": "/works/OL1W"}]}
    work = {"description": {"type": "/type/text", "value": "A dict description."}}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[_mock_response(200, edition), _mock_response(200, work)]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata_by_isbn("1234567890")

    assert result.description == "A dict description."


@pytest.mark.asyncio
async def test_fetch_metadata_by_title_author_success():
    search_result = {
        "docs": [
            {
                "key": "OL893415W",
                "title": "Dune",
                "author_name": ["Frank Herbert"],
                "cover_i": 12345,
                "number_of_pages_median": 688,
                "publisher": ["Ace Books"],
                "subject": ["Science Fiction"],
            }
        ]
    }
    work = {"description": "A desert epic."}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[_mock_response(200, search_result), _mock_response(200, work)]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata_by_title_author("Dune", "Frank Herbert")

    assert result is not None
    assert result.open_library_key == "/works/OL893415W"
    assert result.description == "A desert epic."
    assert result.page_count == 688


@pytest.mark.asyncio
async def test_fetch_metadata_falls_back_to_search():
    """When ISBN is None, should try title+author search."""
    search_result = {
        "docs": [
            {
                "key": "OL1W",
                "title": "Dune",
                "author_name": ["Frank Herbert"],
            }
        ]
    }
    work = {"description": "A classic."}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[_mock_response(200, search_result), _mock_response(200, work)]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata(title="Dune", author="Frank Herbert")

    assert result is not None
    assert result.description == "A classic."


@pytest.mark.asyncio
async def test_fetch_metadata_isbn_preferred_over_search():
    """When ISBN is available, should use it and not fall back to search."""
    edition = {"works": [{"key": "/works/OL1W"}]}
    work = {"description": "ISBN result."}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[_mock_response(200, edition), _mock_response(200, work)]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("shelflife.services.openlibrary.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_metadata(isbn="0441172717", title="Dune", author="Frank Herbert")

    assert result.description == "ISBN result."
    # Should have only made 2 calls (edition + work), not a search call
    assert mock_client.get.call_count == 2
