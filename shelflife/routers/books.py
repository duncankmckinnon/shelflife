from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shelflife.database import get_session
from shelflife.models import Book, BookTag, ShelfBook, Tag
from shelflife.schemas.book import (
    BookCreate,
    BookDetail,
    BookResponse,
    BookUpdate,
    EnrichResponse,
)
from shelflife.services.enrich_service import enrich_book

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/search", response_model=list[BookResponse])
async def search_books(
    title: str = Query(..., description="Title to search for (case-insensitive partial match)"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Book)
        .where(Book.title.ilike(f"%{title}%"))
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Book)
    if author:
        stmt = stmt.where(Book.author.ilike(f"%{author}%"))
    if q:
        stmt = stmt.where(Book.title.ilike(f"%{q}%"))
    if tag:
        stmt = stmt.join(BookTag).join(Tag).where(Tag.name == tag)
    stmt = stmt.order_by(Book.title).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: int, session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Book)
        .where(Book.id == book_id)
        .options(
            selectinload(Book.tags),
            selectinload(Book.reviews),
            selectinload(Book.shelf_links).selectinload(ShelfBook.shelf),
        )
    )
    result = await session.execute(stmt)
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    # Build shelves from shelf_links
    book_dict = BookDetail.model_validate(book).model_dump()
    book_dict["shelves"] = [link.shelf for link in book.shelf_links]
    return BookDetail(**book_dict)


@router.post("", response_model=BookResponse, status_code=201)
async def create_book(
    data: BookCreate,
    enrich: bool = Query(False, description="Fetch metadata from Open Library after creating"),
    session: AsyncSession = Depends(get_session),
):
    book = Book(**data.model_dump())
    session.add(book)
    await session.flush()

    if enrich:
        await enrich_book(session, book)

    await session.commit()
    await session.refresh(book)
    return book


@router.post("/{book_id}/enrich", response_model=EnrichResponse)
async def enrich_book_endpoint(
    book_id: int,
    overwrite: bool = Query(False, description="Overwrite existing fields"),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Book).where(Book.id == book_id))
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
    book_id: int, data: BookUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(book, key, value)
    await session.commit()
    await session.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    await session.delete(book)
    await session.commit()
