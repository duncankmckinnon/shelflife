"""Parse a Goodreads library export CSV into structured data."""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class GoodreadsRow:
    goodreads_id: str
    title: str
    author: str
    additional_authors: str | None
    isbn: str | None
    isbn13: str | None
    publisher: str | None
    page_count: int | None
    year_published: int | None
    rating: int | None
    review_text: str | None
    exclusive_shelf: str | None
    bookshelves: list[str]
    date_added: datetime | None
    date_read: date | None


def _clean_isbn(raw: str | None) -> str | None:
    """Strip the ="" wrapper Goodreads puts around ISBNs."""
    if not raw:
        return None
    cleaned = raw.strip().strip('="').strip('"')
    return cleaned if cleaned else None


def _parse_int(raw: str | None) -> int | None:
    if not raw or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def _parse_date(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y/%m/%d").date()
    except ValueError:
        return None


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y/%m/%d")
    except ValueError:
        return None


def parse_goodreads_csv(content: str) -> list[GoodreadsRow]:
    """Parse a Goodreads CSV export string into a list of GoodreadsRow objects."""
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        rating_val = _parse_int(row.get("My Rating"))
        bookshelves_raw = row.get("Bookshelves", "")
        bookshelves = [s.strip() for s in bookshelves_raw.split(",") if s.strip()]

        rows.append(
            GoodreadsRow(
                goodreads_id=row.get("Book Id", "").strip(),
                title=row.get("Title", "").strip(),
                author=row.get("Author", "").strip(),
                additional_authors=row.get("Additional Authors", "").strip() or None,
                isbn=_clean_isbn(row.get("ISBN")),
                isbn13=_clean_isbn(row.get("ISBN13")),
                publisher=row.get("Publisher", "").strip() or None,
                page_count=_parse_int(row.get("Number of Pages")),
                year_published=_parse_int(row.get("Year Published"))
                or _parse_int(row.get("Original Publication Year")),
                rating=rating_val if rating_val and rating_val > 0 else None,
                review_text=row.get("My Review", "").strip() or None,
                exclusive_shelf=row.get("Exclusive Shelf", "").strip() or None,
                bookshelves=bookshelves,
                date_added=_parse_datetime(row.get("Date Added")),
                date_read=_parse_date(row.get("Date Read")),
            )
        )
    return rows
