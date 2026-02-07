from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.database import get_session
from shelflife.id import make_id
from shelflife.models import Book, BookTag, Tag
from shelflife.schemas.book import BookResponse
from shelflife.schemas.tag import (
    BulkBookTagCreate,
    BulkBookTagResponse,
    BulkTagCreate,
    BulkTagResponse,
    TagCreate,
    TagResponse,
)

router = APIRouter(tags=["tags"])


@router.get("/api/tags", response_model=list[TagResponse])
async def list_tags(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Tag).order_by(Tag.name))
    return result.scalars().all()


@router.get("/api/tags/by-name/{tag_name}/books", response_model=list[BookResponse])
async def get_books_by_tag_name(
    tag_name: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    tag_id = make_id(tag_name)
    return await get_books_by_tag(tag_id, limit, offset, session)


@router.get("/api/tags/{tag_id}/books", response_model=list[BookResponse])
async def get_books_by_tag(
    tag_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    tag = (await session.execute(select(Tag).where(Tag.id == tag_id))).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")

    stmt = (
        select(Book)
        .join(BookTag)
        .where(BookTag.tag_id == tag_id)
        .order_by(Book.title)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/api/books/{book_id}/tags", response_model=TagResponse, status_code=201)
async def tag_book(
    book_id: int, data: TagCreate, session: AsyncSession = Depends(get_session)
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get or create tag
    result = await session.execute(select(Tag).where(Tag.name == data.name))
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = Tag(id=make_id(data.name), name=data.name)
        session.add(tag)
        await session.flush()

    # Check if already tagged
    existing = await session.execute(
        select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Book already has this tag")

    session.add(BookTag(book_id=book_id, tag_id=tag.id))
    await session.commit()
    return tag


@router.post("/api/books/{book_id}/tags/batch", response_model=BulkTagResponse)
async def bulk_tag_book(
    book_id: int, data: BulkTagCreate, session: AsyncSession = Depends(get_session)
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    tags = []
    created = 0
    skipped = 0

    for tag_name in data.tags:
        # Get or create tag
        result = await session.execute(select(Tag).where(Tag.name == tag_name))
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(id=make_id(tag_name), name=tag_name)
            session.add(tag)
            await session.flush()

        # Check if already tagged
        existing = await session.execute(
            select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag.id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
        else:
            session.add(BookTag(book_id=book_id, tag_id=tag.id))
            created += 1

        tags.append(tag)

    await session.commit()
    return BulkTagResponse(tags=tags, created=created, skipped=skipped)


@router.post("/api/tags/books/batch", response_model=BulkBookTagResponse)
async def bulk_tag_books(
    data: BulkBookTagCreate, session: AsyncSession = Depends(get_session)
):
    # Get or create tag
    result = await session.execute(select(Tag).where(Tag.name == data.tag))
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = Tag(id=make_id(data.tag), name=data.tag)
        session.add(tag)
        await session.flush()

    # Fetch all requested books in one query
    books_result = await session.execute(
        select(Book).where(Book.id.in_(data.book_ids))
    )
    found_books = {book.id: book for book in books_result.scalars().all()}
    not_found = [bid for bid in data.book_ids if bid not in found_books]

    tagged = 0
    skipped = 0

    for book_id in found_books:
        existing = await session.execute(
            select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag.id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
        else:
            session.add(BookTag(book_id=book_id, tag_id=tag.id))
            tagged += 1

    await session.commit()
    return BulkBookTagResponse(tag=tag, tagged=tagged, skipped=skipped, not_found=not_found)


@router.delete("/api/books/{book_id}/tags/{tag_id}", status_code=204)
async def untag_book(
    book_id: int, tag_id: int, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Tag not found on this book")
    await session.delete(link)
    await session.commit()
