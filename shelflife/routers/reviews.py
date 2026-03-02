from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.auth import get_current_user
from shelflife.database import get_session
from shelflife.id import make_id
from shelflife.models import Book, Review
from shelflife.models.user import User
from shelflife.schemas.review import (
    RatingUpdate,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
    ReviewWithBook,
)

router = APIRouter(tags=["reviews"])


@router.get("/api/reviews", response_model=list[ReviewWithBook])
async def list_all_reviews(
    rating: float | None = Query(None, ge=0.0, le=5.0, description="Filter by exact rating"),
    min_rating: float | None = Query(None, ge=0.0, le=5.0, description="Filter by minimum rating"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Review, Book.title, Book.author)
        .join(Book)
        .where(Review.user_id == current_user.id, Review.deleted_at.is_(None))
    )
    if rating is not None:
        stmt = stmt.where(Review.rating == rating)
    if min_rating is not None:
        stmt = stmt.where(Review.rating >= min_rating)
    stmt = stmt.order_by(Review.updated_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    rows = result.all()
    return [
        ReviewWithBook(
            id=review.id,
            book_id=review.book_id,
            rating=review.rating,
            review_text=review.review_text,
            created_at=review.created_at,
            updated_at=review.updated_at,
            book_title=title,
            book_author=author,
        )
        for review, title, author in rows
    ]


@router.get("/api/books/{book_id}/review", response_model=ReviewResponse)
async def get_review(
    book_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    review = (await session.execute(
        select(Review).where(
            Review.book_id == book_id,
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/api/books/{book_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    book_id: int,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    existing = (await session.execute(
        select(Review).where(
            Review.book_id == book_id,
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Review already exists for this book")

    review = Review(
        id=make_id(current_user.id, book_id),
        book_id=book_id,
        user_id=current_user.id,
        **data.model_dump(),
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


@router.put("/api/books/{book_id}/rating", response_model=ReviewResponse)
async def quick_rate(
    book_id: int,
    data: RatingUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    book = (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    review = (await session.execute(
        select(Review).where(
            Review.book_id == book_id,
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )).scalar_one_or_none()

    if review is None:
        review = Review(
            id=make_id(current_user.id, book_id),
            book_id=book_id,
            user_id=current_user.id,
            rating=data.rating,
        )
        session.add(review)
    else:
        review.rating = data.rating

    await session.commit()
    await session.refresh(review)
    return review


@router.put("/api/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    review = (await session.execute(
        select(Review).where(
            Review.id == review_id,
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(review, key, value)
    await session.commit()
    await session.refresh(review)
    return review


@router.delete("/api/reviews/{review_id}", status_code=204)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    review = (await session.execute(
        select(Review).where(
            Review.id == review_id,
            Review.user_id == current_user.id,
            Review.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    await session.delete(review)
    await session.commit()
