from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shelflife.database import get_session
from shelflife.id import make_id
from shelflife.models import Book, Reading, ReadingProgress
from shelflife.schemas.book import BulkBookRequest
from shelflife.schemas.reading import (
    BookReadingsResponse,
    FinishReadingRequest,
    ReadingDetail,
    ReadingProgressCreate,
    ReadingProgressResponse,
    ReadingResponse,
    ReadingUpdate,
    StartReadingRequest,
)

router = APIRouter(tags=["reading"])


async def _get_book_or_404(session: AsyncSession, book_id: int) -> Book:
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


async def _get_active_reading(session: AsyncSession, book_id: int) -> Reading:
    result = await session.execute(
        select(Reading)
        .where(Reading.book_id == book_id, Reading.finished_at.is_(None))
        .order_by(Reading.created_at.desc())
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        raise HTTPException(status_code=404, detail="No active reading for this book")
    return reading


async def _get_last_page(session: AsyncSession, reading_id: int) -> int:
    result = await session.execute(
        select(ReadingProgress.page)
        .where(ReadingProgress.reading_id == reading_id)
        .order_by(ReadingProgress.date.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row if row is not None else 0


def _resolve_page(data: ReadingProgressCreate, last_page: int) -> int:
    if data.page is not None:
        return data.page
    if data.pages_read is not None:
        return last_page + data.pages_read
    # start_page + end_page range
    return data.end_page


@router.post("/api/books/bulk-readings", response_model=list[BookReadingsResponse])
async def get_bulk_readings(
    data: BulkBookRequest, session: AsyncSession = Depends(get_session)
):
    id_to_ref = {make_id(b.title, b.author): b for b in data.books}
    result = await session.execute(
        select(Reading)
        .where(Reading.book_id.in_(id_to_ref.keys()))
        .order_by(Reading.book_id, Reading.created_at.desc())
    )
    readings = result.scalars().all()

    grouped: dict[int, list] = defaultdict(list)
    for r in readings:
        grouped[r.book_id].append(ReadingResponse.model_validate(r).model_dump())

    return [
        BookReadingsResponse(
            title=ref.title,
            author=ref.author,
            readings=grouped[book_id],
        )
        for book_id, ref in id_to_ref.items()
    ]


@router.post("/api/books/{book_id}/start-reading", response_model=ReadingResponse, status_code=201)
async def start_reading(
    book_id: int,
    data: StartReadingRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    started = (data.started_at if data and data.started_at else date.today())
    reading_id = make_id(book_id, str(started))

    # Check for duplicate
    existing = (await session.execute(select(Reading).where(Reading.id == reading_id))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A reading with this start date already exists")

    reading = Reading(id=reading_id, book_id=book_id, started_at=started)
    session.add(reading)
    await session.commit()
    await session.refresh(reading)
    return reading


@router.put("/api/books/{book_id}/finish-reading", response_model=ReadingResponse)
async def finish_reading(
    book_id: int,
    data: FinishReadingRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    reading = await _get_active_reading(session, book_id)
    reading.finished_at = data.finished_at if data and data.finished_at else date.today()
    await session.commit()
    await session.refresh(reading)
    return reading


@router.get("/api/books/{book_id}/readings", response_model=list[ReadingResponse])
async def list_readings(
    book_id: int,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    result = await session.execute(
        select(Reading).where(Reading.book_id == book_id).order_by(Reading.created_at.desc())
    )
    return result.scalars().all()


@router.get("/api/books/{book_id}/readings/{reading_id}", response_model=ReadingDetail)
async def get_reading(
    book_id: int,
    reading_id: int,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    result = await session.execute(
        select(Reading)
        .where(Reading.id == reading_id, Reading.book_id == book_id)
        .options(selectinload(Reading.progress_entries))
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading


@router.put("/api/books/{book_id}/readings/{reading_id}", response_model=ReadingResponse)
async def update_reading(
    book_id: int,
    reading_id: int,
    data: ReadingUpdate,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id, Reading.book_id == book_id)
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(reading, key, value)
    await session.commit()
    await session.refresh(reading)
    return reading


@router.delete("/api/books/{book_id}/readings/{reading_id}", status_code=204)
async def delete_reading(
    book_id: int,
    reading_id: int,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id, Reading.book_id == book_id)
    )
    reading = result.scalar_one_or_none()
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    await session.delete(reading)
    await session.commit()


@router.post(
    "/api/books/{book_id}/reading/progress",
    response_model=ReadingProgressResponse,
    status_code=201,
)
async def log_progress(
    book_id: int,
    data: ReadingProgressCreate,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    reading = await _get_active_reading(session, book_id)

    progress_date = data.date if data.date else date.today()
    last_page = await _get_last_page(session, reading.id)
    page = _resolve_page(data, last_page)

    progress_id = make_id(reading.id, str(progress_date))

    # Check for duplicate date
    existing = (
        await session.execute(select(ReadingProgress).where(ReadingProgress.id == progress_id))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Progress already logged for this date")

    progress = ReadingProgress(
        id=progress_id, reading_id=reading.id, page=page, date=progress_date
    )
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    return progress


@router.get(
    "/api/books/{book_id}/reading/progress",
    response_model=list[ReadingProgressResponse],
)
async def get_active_progress(
    book_id: int,
    session: AsyncSession = Depends(get_session),
):
    await _get_book_or_404(session, book_id)
    reading = await _get_active_reading(session, book_id)
    result = await session.execute(
        select(ReadingProgress)
        .where(ReadingProgress.reading_id == reading.id)
        .order_by(ReadingProgress.date)
    )
    return result.scalars().all()


@router.delete("/api/reading/progress/{progress_id}", status_code=204)
async def delete_progress(
    progress_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ReadingProgress).where(ReadingProgress.id == progress_id)
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        raise HTTPException(status_code=404, detail="Progress entry not found")
    await session.delete(progress)
    await session.commit()
