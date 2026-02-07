"""Apply Open Library metadata to books in the database."""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.models import Book, BookTag, Tag
from shelflife.services.openlibrary import fetch_metadata

logger = logging.getLogger(__name__)


@dataclass
class EnrichResult:
    book_id: int
    enriched: bool
    fields_updated: list[str] = field(default_factory=list)
    tags_added: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class BatchEnrichResult:
    total: int
    enriched: int
    failed: int
    results: list[EnrichResult] = field(default_factory=list)


async def enrich_book(
    session: AsyncSession,
    book: Book,
    overwrite: bool = False,
) -> EnrichResult:
    """Fetch Open Library metadata and apply it to a Book.

    Only fills blank fields unless overwrite=True.
    Auto-creates tags from Open Library subjects.
    """
    result = EnrichResult(book_id=book.id, enriched=False)

    metadata = await fetch_metadata(
        isbn=book.isbn,
        isbn13=book.isbn13,
        title=book.title,
        author=book.author,
    )

    if metadata is None:
        result.error = "No metadata found"
        return result

    field_map = {
        "description": metadata.description,
        "cover_url": metadata.cover_url,
        "page_count": metadata.page_count,
        "publisher": metadata.publisher,
        "year_published": metadata.publish_year,
        "open_library_key": metadata.open_library_key,
    }

    for field_name, new_value in field_map.items():
        if new_value is None:
            continue
        current = getattr(book, field_name, None)
        if current is None or overwrite:
            setattr(book, field_name, new_value)
            result.fields_updated.append(field_name)

    for subject_name in metadata.subjects[:10]:
        tag_name = subject_name.strip().lower()
        if not tag_name or len(tag_name) > 100:
            continue

        tag_result = await session.execute(select(Tag).where(Tag.name == tag_name))
        tag = tag_result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name=tag_name)
            session.add(tag)
            await session.flush()

        existing_link = await session.execute(
            select(BookTag).where(BookTag.book_id == book.id, BookTag.tag_id == tag.id)
        )
        if existing_link.scalar_one_or_none() is None:
            session.add(BookTag(book_id=book.id, tag_id=tag.id))
            result.tags_added.append(tag_name)

    result.enriched = bool(result.fields_updated or result.tags_added)
    return result


async def enrich_books_batch(
    session: AsyncSession,
    book_ids: list[int] | None = None,
    only_unenriched: bool = True,
    overwrite: bool = False,
) -> BatchEnrichResult:
    """Enrich multiple books. Sequential to respect Open Library rate limits."""
    stmt = select(Book)
    if book_ids:
        stmt = stmt.where(Book.id.in_(book_ids))
    elif only_unenriched:
        stmt = stmt.where(Book.open_library_key.is_(None))

    books = (await session.execute(stmt)).scalars().all()

    batch = BatchEnrichResult(total=len(books), enriched=0, failed=0)

    for book in books:
        enrich_result = await enrich_book(session, book, overwrite=overwrite)
        batch.results.append(enrich_result)
        if enrich_result.enriched:
            batch.enriched += 1
        elif enrich_result.error:
            batch.failed += 1

    await session.commit()
    return batch
