from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    review_text: str | None = None


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    review_text: str | None = None


class RatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    rating: int | None
    review_text: str | None
    created_at: datetime
    updated_at: datetime


class ReviewWithBook(ReviewResponse):
    book_title: str
    book_author: str
