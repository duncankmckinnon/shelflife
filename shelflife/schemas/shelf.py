from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShelfCreate(BaseModel):
    name: str
    description: str | None = None
    is_exclusive: bool = False


class ShelfUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ShelfResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_exclusive: bool
    created_at: datetime


class ShelfWithBooks(ShelfResponse):
    books: list["BookResponse"] = []


from shelflife.schemas.book import BookResponse  # noqa: E402

ShelfWithBooks.model_rebuild()
