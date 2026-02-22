from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: float | None = Field(None, ge=0.0, le=5.0)
    review_text: str | None = None


class ReviewUpdate(BaseModel):
    rating: float | None = Field(None, ge=0.0, le=5.0)
    review_text: str | None = None


class RatingUpdate(BaseModel):
    rating: float = Field(ge=0.0, le=5.0)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    rating: float | None
    review_text: str | None
    created_at: datetime
    updated_at: datetime


class ReviewWithBook(ReviewResponse):
    book_title: str
    book_author: str
