"""Import parsed Goodreads data into the database."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.id import make_id
from shelflife.models import Book, Reading, Review, Shelf, ShelfBook
from shelflife.services.goodreads import GoodreadsRow


@dataclass
class ImportResult:
    books_created: int = 0
    books_updated: int = 0
    shelves_created: int = 0
    reviews_created: int = 0
    readings_created: int = 0


async def _get_or_create_shelf(
    session: AsyncSession, name: str, is_exclusive: bool = False
) -> Shelf:
    result = await session.execute(select(Shelf).where(Shelf.name == name))
    shelf = result.scalar_one_or_none()
    if shelf is None:
        shelf = Shelf(id=make_id(name), name=name, is_exclusive=is_exclusive)
        session.add(shelf)
        await session.flush()
    return shelf


async def import_goodreads_rows(
    session: AsyncSession, rows: list[GoodreadsRow]
) -> ImportResult:
    result = ImportResult()
    exclusive_shelf_names = {"read", "currently-reading", "to-read"}

    for row in rows:
        if not row.goodreads_id or not row.title:
            continue

        # Upsert book by goodreads_id
        existing = await session.execute(
            select(Book).where(Book.goodreads_id == row.goodreads_id)
        )
        book = existing.scalar_one_or_none()

        if book is None:
            book = Book(
                id=make_id(row.title, row.author),
                title=row.title,
                author=row.author,
                additional_authors=row.additional_authors,
                isbn=row.isbn,
                isbn13=row.isbn13,
                publisher=row.publisher,
                page_count=row.page_count,
                year_published=row.year_published,
                goodreads_id=row.goodreads_id,
            )
            session.add(book)
            await session.flush()
            result.books_created += 1
        else:
            book.title = row.title
            book.author = row.author
            book.additional_authors = row.additional_authors
            book.isbn = row.isbn
            book.isbn13 = row.isbn13
            book.publisher = row.publisher
            book.page_count = row.page_count
            book.year_published = row.year_published
            result.books_updated += 1

        # Create shelves and associations
        all_shelf_names = set(row.bookshelves)
        if row.exclusive_shelf:
            all_shelf_names.add(row.exclusive_shelf)

        for shelf_name in all_shelf_names:
            is_excl = shelf_name in exclusive_shelf_names
            shelf = await _get_or_create_shelf(session, shelf_name, is_excl)

            # Check if association already exists
            existing_link = await session.execute(
                select(ShelfBook).where(
                    ShelfBook.shelf_id == shelf.id,
                    ShelfBook.book_id == book.id,
                )
            )
            if existing_link.scalar_one_or_none() is None:
                link = ShelfBook(
                    id=make_id(shelf.id, book.id),
                    shelf_id=shelf.id,
                    book_id=book.id,
                    date_added=row.date_added,
                    date_read=row.date_read,
                )
                session.add(link)
                result.shelves_created += 1

        # Create reading if date_read is present
        if row.date_read:
            started_at = row.date_added.date() if row.date_added and row.exclusive_shelf == "read" else None
            reading_id = make_id(book.id, str(row.date_read))
            existing_reading = await session.execute(
                select(Reading).where(Reading.id == reading_id)
            )
            if existing_reading.scalar_one_or_none() is None:
                reading = Reading(
                    id=reading_id,
                    book_id=book.id,
                    started_at=started_at,
                    finished_at=row.date_read,
                )
                session.add(reading)
                result.readings_created += 1

        # Create review if rated or reviewed
        if row.rating or row.review_text:
            existing_review = await session.execute(
                select(Review).where(Review.book_id == book.id)
            )
            if existing_review.scalar_one_or_none() is None:
                review = Review(
                    id=make_id(book.id),
                    book_id=book.id,
                    rating=row.rating,
                    review_text=row.review_text,
                )
                session.add(review)
                result.reviews_created += 1

    await session.commit()
    return result
