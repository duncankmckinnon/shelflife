from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.auth import get_current_user
from shelflife.database import get_session
from shelflife.id import make_id
from shelflife.models import Book, BookTag, Tag
from shelflife.models.user import User
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


def _tag_id(is_public: bool, user_id: int, name: str) -> int:
    """Deterministic tag ID: public tags hash on name only; private tags hash on (user_id, name)."""
    return make_id(name) if is_public else make_id(user_id, name)


async def _get_or_create_tag(
    session: AsyncSession,
    name: str,
    is_public: bool,
    user_id: int,
) -> Tag:
    """Find an existing tag or create one, respecting public/private distinction."""
    if is_public:
        # Public tags are community-shared: matched by name with NULL user_id
        stmt = select(Tag).where(Tag.name == name, Tag.user_id.is_(None), Tag.is_public.is_(True))
    else:
        # Private tags are user-scoped
        stmt = select(Tag).where(Tag.name == name, Tag.user_id == user_id, Tag.is_public.is_(False))

    tag = (await session.execute(stmt)).scalar_one_or_none()
    if tag is None:
        tag = Tag(
            id=_tag_id(is_public, user_id, name),
            name=name,
            is_public=is_public,
            user_id=None if is_public else user_id,
        )
        session.add(tag)
        await session.flush()
    return tag


@router.get("/api/tags", response_model=list[TagResponse])
async def list_tags(
    public_only: bool = Query(False, description="Return only public/community tags"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List tags visible to the current user: public tags + their own private tags."""
    if public_only:
        stmt = select(Tag).where(Tag.is_public.is_(True), Tag.deleted_at.is_(None)).order_by(Tag.name)
    else:
        stmt = (
            select(Tag)
            .where(
                Tag.deleted_at.is_(None),
                (Tag.is_public.is_(True)) | (Tag.user_id == current_user.id),
            )
            .order_by(Tag.name)
        )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/api/tags/by-name/{tag_name}/books", response_model=list[BookResponse])
async def get_books_by_tag_name(
    tag_name: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    # Look up public tag by name
    tag = (await session.execute(
        select(Tag).where(Tag.name == tag_name, Tag.is_public.is_(True), Tag.deleted_at.is_(None))
    )).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return await _books_for_tag(tag.id, limit, offset, session)


@router.get("/api/tags/{tag_id}/books", response_model=list[BookResponse])
async def get_books_by_tag(
    tag_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    tag = (await session.execute(
        select(Tag).where(Tag.id == tag_id, Tag.deleted_at.is_(None))
    )).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return await _books_for_tag(tag_id, limit, offset, session)


async def _books_for_tag(
    tag_id: int,
    limit: int,
    offset: int,
    session: AsyncSession,
) -> list[Book]:
    stmt = (
        select(Book)
        .join(BookTag)
        .where(BookTag.tag_id == tag_id, Book.deleted_at.is_(None))
        .order_by(Book.title)
        .offset(offset)
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()


@router.post("/api/books/{book_id}/tags", response_model=TagResponse, status_code=201)
async def tag_book(
    book_id: int,
    data: TagCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    tag = await _get_or_create_tag(session, data.name, data.is_public, current_user.id)

    existing = (await session.execute(
        select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag.id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Book already has this tag")

    session.add(BookTag(book_id=book_id, tag_id=tag.id, user_id=current_user.id))
    await session.commit()
    return tag


@router.post("/api/books/{book_id}/tags/batch", response_model=BulkTagResponse)
async def bulk_tag_book(
    book_id: int,
    data: BulkTagCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    tags = []
    created = 0
    skipped = 0

    # Bulk endpoint creates private tags (user-owned); use is_public=False
    for tag_name in data.tags:
        tag = await _get_or_create_tag(session, tag_name, is_public=False, user_id=current_user.id)

        existing = (await session.execute(
            select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag.id)
        )).scalar_one_or_none()
        if existing:
            skipped += 1
        else:
            session.add(BookTag(book_id=book_id, tag_id=tag.id, user_id=current_user.id))
            created += 1

        tags.append(tag)

    await session.commit()
    return BulkTagResponse(tags=tags, created=created, skipped=skipped)


@router.post("/api/tags/books/batch", response_model=BulkBookTagResponse)
async def bulk_tag_books(
    data: BulkBookTagCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Bulk-apply a single private tag to many books
    tag = await _get_or_create_tag(session, data.tag, is_public=False, user_id=current_user.id)

    books_result = await session.execute(
        select(Book).where(Book.id.in_(data.book_ids))
    )
    found_books = {book.id: book for book in books_result.scalars().all()}
    not_found = [bid for bid in data.book_ids if bid not in found_books]

    tagged = 0
    skipped = 0

    for book_id in found_books:
        existing = (await session.execute(
            select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag.id)
        )).scalar_one_or_none()
        if existing:
            skipped += 1
        else:
            session.add(BookTag(book_id=book_id, tag_id=tag.id, user_id=current_user.id))
            tagged += 1

    await session.commit()
    return BulkBookTagResponse(tag=tag, tagged=tagged, skipped=skipped, not_found=not_found)


@router.delete("/api/books/{book_id}/tags/{tag_id}", status_code=204)
async def untag_book(
    book_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    link = (await session.execute(
        select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag_id)
    )).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Tag not found on this book")
    await session.delete(link)
    await session.commit()
