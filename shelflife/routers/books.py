from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shelflife.auth import get_current_user
from shelflife.database import get_session
from shelflife.id import make_id
from shelflife.models import Book, BookTag, Reading, Review, ShelfBook, Tag
from shelflife.models.user import User
from shelflife.models.user_book import ensure_user_book
from shelflife.schemas.book import (
    BookCreate,
    BookDetail,
    BookLookupResult,
    BookResponse,
    BookUpdate,
    BulkBookRequest,
    EnrichResponse,
)
from shelflife.services.enrich_service import enrich_book
from shelflife.services.openlibrary import search_candidates

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/stats")
async def book_stats(session: AsyncSession = Depends(get_session)):
    total = (await session.execute(
        select(func.count(Book.id)).where(Book.deleted_at.is_(None))
    )).scalar()
    return {"total_books": total}


@router.get("/search", response_model=list[BookResponse])
async def search_books(
    title: str = Query(..., description="Title to search for (case-insensitive partial match)"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Book)
        .where(Book.title.ilike(f"%{title}%"), Book.deleted_at.is_(None))
        .order_by(Book.title)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("", response_model=list[BookResponse])
async def list_books(
    author: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    started_after: date | None = Query(None, description="Filter books with a reading started on or after this date (YYYY-MM-DD)"),
    started_before: date | None = Query(None, description="Filter books with a reading started on or before this date (YYYY-MM-DD)"),
    finished_after: date | None = Query(None, description="Filter books with a reading finished on or after this date (YYYY-MM-DD)"),
    finished_before: date | None = Query(None, description="Filter books with a reading finished on or before this date (YYYY-MM-DD)"),
    sort: Literal["title", "author", "created_at"] = "title",
    order: Literal["asc", "desc"] = "asc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Book).distinct().where(Book.deleted_at.is_(None))
    if author:
        stmt = stmt.where(Book.author.ilike(f"%{author}%"))
    if q:
        stmt = stmt.where(Book.title.ilike(f"%{q}%"))
    if tag:
        stmt = stmt.join(BookTag).join(Tag).where(Tag.name == tag)
    if started_after or started_before or finished_after or finished_before:
        stmt = stmt.join(Reading, Reading.book_id == Book.id)
        if started_after:
            stmt = stmt.where(Reading.started_at >= started_after)
        if started_before:
            stmt = stmt.where(Reading.started_at <= started_before)
        if finished_after:
            stmt = stmt.where(Reading.finished_at >= finished_after)
        if finished_before:
            stmt = stmt.where(Reading.finished_at <= finished_before)
    col = getattr(Book, sort)
    stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/lookup", response_model=list[BookLookupResult])
async def lookup_book(
    title: str = Query(..., description="Book title to search for"),
    author: str | None = Query(None, description="Author name (optional but recommended)"),
    limit: int = Query(5, ge=1, le=10),
):
    candidates = await search_candidates(title, author, limit=limit)
    return [
        BookLookupResult(
            title=c.title,
            author=c.author,
            open_library_key=c.open_library_key,
            cover_url=c.cover_url,
            isbn=c.isbn,
            isbn13=c.isbn13,
            publisher=c.publisher,
            year_published=c.year_published,
            page_count=c.page_count,
        )
        for c in candidates
    ]


@router.post("/bulk", response_model=list[BookDetail])
async def get_books_bulk(
    data: BulkBookRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ids = [make_id(b.title, b.author) for b in data.books]
    stmt = (
        select(Book)
        .where(Book.id.in_(ids), Book.deleted_at.is_(None))
        .options(
            selectinload(Book.tags),
            selectinload(Book.shelf_links).selectinload(ShelfBook.shelf),
        )
    )
    result = await session.execute(stmt)
    books = result.scalars().all()

    # Fetch this user's reviews for these books in one query
    reviews_result = await session.execute(
        select(Review).where(
            Review.book_id.in_(ids),
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )
    review_by_book = {r.book_id: r for r in reviews_result.scalars().all()}

    out = []
    for book in books:
        book_dict = BookDetail.model_validate(book).model_dump()
        book_dict["shelves"] = [link.shelf for link in book.shelf_links]
        book_dict["review"] = review_by_book.get(book.id)
        out.append(BookDetail(**book_dict))
    return out


@router.get("/by-name/{title}/{author}", response_model=BookDetail)
async def get_book_by_name(
    title: str,
    author: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    book_id = make_id(title, author)
    return await _get_book_detail(book_id, current_user, session)


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _get_book_detail(book_id, current_user, session)


async def _get_book_detail(book_id: int, current_user: User, session: AsyncSession) -> BookDetail:
    stmt = (
        select(Book)
        .where(Book.id == book_id, Book.deleted_at.is_(None))
        .options(
            selectinload(Book.tags),
            selectinload(Book.shelf_links).selectinload(ShelfBook.shelf),
        )
    )
    result = await session.execute(stmt)
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    review = (await session.execute(
        select(Review).where(
            Review.book_id == book_id,
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    book_dict = BookDetail.model_validate(book).model_dump()
    book_dict["shelves"] = [link.shelf for link in book.shelf_links]
    book_dict["review"] = review
    return BookDetail(**book_dict)


@router.post("", response_model=BookResponse, status_code=201)
async def create_book(
    data: BookCreate,
    enrich: bool = Query(False, description="Fetch metadata from Open Library after creating"),
    resolve: bool = Query(False, description="Resolve canonical title/author from Open Library before creating"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if resolve:
        candidates = await search_candidates(data.title, data.author, limit=1)
        if candidates:
            best = candidates[0]
            data = data.model_copy(update={"title": best.title, "author": best.author})
            for field_name in ("isbn", "isbn13", "publisher", "page_count", "year_published", "cover_url"):
                if getattr(data, field_name) is None and getattr(best, field_name) is not None:
                    data = data.model_copy(update={field_name: getattr(best, field_name)})

    book_id = make_id(data.title, data.author)
    existing = await session.get(Book, book_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Book already exists")

    book = Book(id=book_id, **data.model_dump())
    session.add(book)
    await session.flush()

    await ensure_user_book(session, current_user.id, book_id)

    if enrich:
        await enrich_book(session, book)

    await session.commit()
    await session.refresh(book)
    return book


@router.post("/{book_id}/enrich", response_model=EnrichResponse)
async def enrich_book_endpoint(
    book_id: int,
    overwrite: bool = Query(False, description="Overwrite existing fields"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    enrich_result = await enrich_book(session, book, overwrite=overwrite)
    await session.commit()

    return EnrichResponse(
        book_id=enrich_result.book_id,
        enriched=enrich_result.enriched,
        fields_updated=enrich_result.fields_updated,
        tags_added=enrich_result.tags_added,
        error=enrich_result.error,
    )


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    data: BookUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(book, key, value)
    await session.commit()
    await session.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Book).where(Book.id == book_id, Book.deleted_at.is_(None))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    await session.delete(book)
    await session.commit()
