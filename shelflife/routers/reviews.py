from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.database import get_session
from shelflife.models import Book, Review
from shelflife.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter(tags=["reviews"])


@router.get("/api/books/{book_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews(book_id: int, session: AsyncSession = Depends(get_session)):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    result = await session.execute(select(Review).where(Review.book_id == book_id))
    return result.scalars().all()


@router.post("/api/books/{book_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    book_id: int, data: ReviewCreate, session: AsyncSession = Depends(get_session)
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    review = Review(book_id=book_id, **data.model_dump())
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


@router.put("/api/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int, data: ReviewUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(review, key, value)
    await session.commit()
    await session.refresh(review)
    return review


@router.delete("/api/reviews/{review_id}", status_code=204)
async def delete_review(review_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    await session.delete(review)
    await session.commit()
