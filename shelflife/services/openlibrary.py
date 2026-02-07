"""Open Library API client for fetching book metadata."""

import logging
import re
from dataclasses import dataclass, field

import httpx

from shelflife.config import (
    OPENLIBRARY_BASE_URL,
    OPENLIBRARY_COVERS_URL,
    OPENLIBRARY_TIMEOUT,
)

logger = logging.getLogger(__name__)


@dataclass
class OpenLibraryMetadata:
    """Enrichment data fetched from Open Library."""

    open_library_key: str | None = None
    description: str | None = None
    cover_url: str | None = None
    page_count: int | None = None
    publisher: str | None = None
    publish_year: int | None = None
    subjects: list[str] = field(default_factory=list)


def _extract_year(publish_date: str | None) -> int | None:
    """Extract a 4-digit year from Open Library's freeform publish_date field."""
    if not publish_date:
        return None
    match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", publish_date)
    return int(match.group(1)) if match else None


def _extract_description(data: dict) -> str | None:
    """Handle Open Library description which can be a string or a dict."""
    desc = data.get("description")
    if isinstance(desc, dict):
        return desc.get("value")
    if isinstance(desc, str):
        return desc
    return None


def _pick_best_match(docs: list[dict], title: str, author: str) -> dict | None:
    """Score search results and return the best match."""
    title_lower = title.lower().strip()
    author_lower = author.lower().strip()

    scored = []
    for doc in docs:
        score = 0
        doc_title = (doc.get("title") or "").lower().strip()
        doc_authors = [a.lower() for a in (doc.get("author_name") or [])]

        if doc_title == title_lower:
            score += 10
        elif title_lower in doc_title or doc_title in title_lower:
            score += 5

        if any(author_lower in a or a in author_lower for a in doc_authors):
            score += 5

        if doc.get("cover_i"):
            score += 1
        if doc.get("number_of_pages_median"):
            score += 1

        if score > 0:
            scored.append((score, doc))

    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


async def fetch_metadata_by_isbn(isbn: str) -> OpenLibraryMetadata | None:
    """Look up a book by ISBN via edition endpoint, then fetch work details."""
    try:
        async with httpx.AsyncClient(timeout=OPENLIBRARY_TIMEOUT) as client:
            resp = await client.get(
                f"{OPENLIBRARY_BASE_URL}/isbn/{isbn}.json",
                follow_redirects=True,
            )
            if resp.status_code != 200:
                logger.warning("Open Library ISBN lookup failed: %s -> %d", isbn, resp.status_code)
                return None

            edition = resp.json()

            metadata = OpenLibraryMetadata(
                page_count=edition.get("number_of_pages"),
                publisher=(edition.get("publishers") or [None])[0],
                publish_year=_extract_year(edition.get("publish_date")),
                cover_url=f"{OPENLIBRARY_COVERS_URL}/b/isbn/{isbn}-L.jpg",
            )

            works = edition.get("works", [])
            if works:
                work_key = works[0]["key"]
                metadata.open_library_key = work_key
                work_resp = await client.get(f"{OPENLIBRARY_BASE_URL}{work_key}.json")
                if work_resp.status_code == 200:
                    work = work_resp.json()
                    metadata.description = _extract_description(work)
                    metadata.subjects = (work.get("subjects") or [])[:20]

            return metadata
    except httpx.HTTPError as e:
        logger.error("Open Library API error for ISBN %s: %s", isbn, e)
        return None


async def fetch_metadata_by_title_author(title: str, author: str) -> OpenLibraryMetadata | None:
    """Fallback search when no ISBN is available."""
    try:
        async with httpx.AsyncClient(timeout=OPENLIBRARY_TIMEOUT) as client:
            resp = await client.get(
                f"{OPENLIBRARY_BASE_URL}/search.json",
                params={"title": title, "author": author, "limit": 5},
            )
            if resp.status_code != 200:
                return None

            docs = resp.json().get("docs", [])
            if not docs:
                return None

            best = _pick_best_match(docs, title, author)
            if best is None:
                return None

            work_key = f"/works/{best['key']}"
            metadata = OpenLibraryMetadata(
                open_library_key=work_key,
                subjects=[s for s in (best.get("subject") or [])[:20]],
            )

            if best.get("cover_i"):
                metadata.cover_url = f"{OPENLIBRARY_COVERS_URL}/b/id/{best['cover_i']}-L.jpg"
            if best.get("number_of_pages_median"):
                metadata.page_count = best["number_of_pages_median"]
            if best.get("publisher"):
                metadata.publisher = best["publisher"][0]

            work_resp = await client.get(f"{OPENLIBRARY_BASE_URL}{work_key}.json")
            if work_resp.status_code == 200:
                metadata.description = _extract_description(work_resp.json())

            return metadata
    except httpx.HTTPError as e:
        logger.error("Open Library search error for '%s' by '%s': %s", title, author, e)
        return None


async def fetch_metadata(
    isbn: str | None = None,
    isbn13: str | None = None,
    title: str | None = None,
    author: str | None = None,
) -> OpenLibraryMetadata | None:
    """Try ISBN lookup first (isbn13 preferred), fall back to title+author search."""
    for candidate_isbn in [isbn13, isbn]:
        if candidate_isbn:
            result = await fetch_metadata_by_isbn(candidate_isbn)
            if result is not None:
                return result

    if title and author:
        return await fetch_metadata_by_title_author(title, author)

    return None
