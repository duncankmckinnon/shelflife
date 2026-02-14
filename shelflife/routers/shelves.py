from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shelflife.database import get_session
from shelflife.id import make_id
from shelflife.models import Book, Shelf, ShelfBook
from shelflife.schemas.book import BookResponse, MoveBookRequest
from shelflife.schemas.shelf import ShelfCreate, ShelfResponse, ShelfUpdate, ShelfWithBooks

router = APIRouter(prefix="/api/shelves", tags=["shelves"])


@router.get("", response_model=list[ShelfResponse])
async def list_shelves(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Shelf).order_by(Shelf.name))
    return result.scalars().all()


@router.get("/by-name/{shelf_name}", response_model=ShelfWithBooks)
async def get_shelf_by_name(
    shelf_name: str, session: AsyncSession = Depends(get_session)
):
    shelf_id = make_id(shelf_name)
    return await get_shelf(shelf_id, session)


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
    shelf = Shelf(id=make_id(data.name), **data.model_dump())
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


@router.post("/move-book/{book_id}")
async def move_book_between_shelves(
    book_id: int,
    data: MoveBookRequest,
    session: AsyncSession = Depends(get_session),
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    from_shelf = (await session.execute(
        select(Shelf).where(Shelf.id == data.from_shelf_id)
    )).scalar_one_or_none()
    if from_shelf is None:
        raise HTTPException(status_code=404, detail="Source shelf not found")

    to_shelf = (await session.execute(
        select(Shelf).where(Shelf.id == data.to_shelf_id)
    )).scalar_one_or_none()
    if to_shelf is None:
        raise HTTPException(status_code=404, detail="Destination shelf not found")

    source_link = (await session.execute(
        select(ShelfBook).where(
            ShelfBook.shelf_id == data.from_shelf_id,
            ShelfBook.book_id == book_id,
        )
    )).scalar_one_or_none()
    if source_link is None:
        raise HTTPException(status_code=404, detail="Book not on source shelf")

    dest_link = (await session.execute(
        select(ShelfBook).where(
            ShelfBook.shelf_id == data.to_shelf_id,
            ShelfBook.book_id == book_id,
        )
    )).scalar_one_or_none()
    if dest_link is not None:
        raise HTTPException(status_code=409, detail="Book already on destination shelf")

    date_added = source_link.date_added
    date_read = source_link.date_read
    await session.delete(source_link)
    new_link = ShelfBook(
        id=make_id(data.to_shelf_id, book_id),
        shelf_id=data.to_shelf_id,
        book_id=book_id,
        date_added=date_added,
        date_read=date_read,
    )
    session.add(new_link)
    await session.commit()
    return {"detail": f"Book moved from '{from_shelf.name}' to '{to_shelf.name}'"}


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

    # Enforce exclusive shelf: remove book from other exclusive shelves
    if shelf.is_exclusive:
        exclusive_links = (await session.execute(
            select(ShelfBook)
            .join(Shelf, ShelfBook.shelf_id == Shelf.id)
            .where(ShelfBook.book_id == book_id, Shelf.is_exclusive.is_(True))
        )).scalars().all()
        for link in exclusive_links:
            await session.delete(link)

    link = ShelfBook(id=make_id(shelf_id, book_id), shelf_id=shelf_id, book_id=book_id)
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
