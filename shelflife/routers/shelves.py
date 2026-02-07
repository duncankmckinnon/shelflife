from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shelflife.database import get_session
from shelflife.models import Book, Shelf, ShelfBook
from shelflife.schemas.book import BookResponse
from shelflife.schemas.shelf import ShelfCreate, ShelfResponse, ShelfUpdate, ShelfWithBooks

router = APIRouter(prefix="/api/shelves", tags=["shelves"])


@router.get("", response_model=list[ShelfResponse])
async def list_shelves(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Shelf).order_by(Shelf.name))
    return result.scalars().all()


@router.get("/{shelf_id}", response_model=ShelfWithBooks)
async def get_shelf(shelf_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Shelf)
        .where(Shelf.id == shelf_id)
        .options(selectinload(Shelf.book_links).selectinload(ShelfBook.book))
    )
    shelf = result.scalar_one_or_none()
    if shelf is None:
        raise HTTPException(status_code=404, detail="Shelf not found")
    shelf_dict = ShelfResponse.model_validate(shelf).model_dump()
    shelf_dict["books"] = [link.book for link in shelf.book_links]
    return ShelfWithBooks(**shelf_dict)


@router.post("", response_model=ShelfResponse, status_code=201)
async def create_shelf(
    data: ShelfCreate, session: AsyncSession = Depends(get_session)
):
    shelf = Shelf(**data.model_dump())
    session.add(shelf)
    await session.commit()
    await session.refresh(shelf)
    return shelf


@router.put("/{shelf_id}", response_model=ShelfResponse)
async def update_shelf(
    shelf_id: int, data: ShelfUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Shelf).where(Shelf.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if shelf is None:
        raise HTTPException(status_code=404, detail="Shelf not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(shelf, key, value)
    await session.commit()
    await session.refresh(shelf)
    return shelf


@router.delete("/{shelf_id}", status_code=204)
async def delete_shelf(shelf_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Shelf).where(Shelf.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if shelf is None:
        raise HTTPException(status_code=404, detail="Shelf not found")
    await session.delete(shelf)
    await session.commit()


@router.post("/{shelf_id}/books/{book_id}", status_code=201)
async def add_book_to_shelf(
    shelf_id: int, book_id: int, session: AsyncSession = Depends(get_session)
):
    # Verify both exist
    shelf = (await session.execute(select(Shelf).where(Shelf.id == shelf_id))).scalar_one_or_none()
    if shelf is None:
        raise HTTPException(status_code=404, detail="Shelf not found")
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check for duplicate
    existing = await session.execute(
        select(ShelfBook).where(ShelfBook.shelf_id == shelf_id, ShelfBook.book_id == book_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Book already on this shelf")

    link = ShelfBook(shelf_id=shelf_id, book_id=book_id)
    session.add(link)
    await session.commit()
    return {"detail": "Book added to shelf"}


@router.delete("/{shelf_id}/books/{book_id}", status_code=204)
async def remove_book_from_shelf(
    shelf_id: int, book_id: int, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(ShelfBook).where(ShelfBook.shelf_id == shelf_id, ShelfBook.book_id == book_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Book not on this shelf")
    await session.delete(link)
    await session.commit()
