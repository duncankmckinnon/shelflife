from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.database import get_session
from shelflife.models import Book, BookTag, Tag
from shelflife.schemas.tag import TagCreate, TagResponse

router = APIRouter(tags=["tags"])


@router.get("/api/tags", response_model=list[TagResponse])
async def list_tags(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Tag).order_by(Tag.name))
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
        tag = Tag(name=data.name)
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
