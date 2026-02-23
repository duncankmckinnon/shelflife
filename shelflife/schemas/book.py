from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    title: str
    author: str
    additional_authors: str | None = None
    isbn: str | None = None
    isbn13: str | None = None
    publisher: str | None = None
    page_count: int | None = None
    year_published: int | None = None
    description: str | None = None
    cover_url: str | None = None


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    additional_authors: str | None = None
    isbn: str | None = None
    isbn13: str | None = None
    publisher: str | None = None
    page_count: int | None = None
    year_published: int | None = None
    description: str | None = None
    cover_url: str | None = None


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    additional_authors: str | None
    isbn: str | None
    isbn13: str | None
    publisher: str | None
    page_count: int | None
    year_published: int | None
    description: str | None
    cover_url: str | None
    goodreads_id: str | None
    open_library_key: str | None
    created_at: datetime
    updated_at: datetime


class BookDetail(BookResponse):
    tags: list["TagResponse"] = []
    shelves: list["ShelfResponse"] = []
    review: "ReviewResponse | None" = None


from shelflife.schemas.tag import TagResponse  # noqa: E402
from shelflife.schemas.shelf import ShelfResponse  # noqa: E402
from shelflife.schemas.review import ReviewResponse  # noqa: E402

BookDetail.model_rebuild()


class EnrichResponse(BaseModel):
    book_id: int
    enriched: bool
    fields_updated: list[str]
    tags_added: list[str]
    error: str | None = None


class BatchEnrichRequest(BaseModel):
    book_ids: list[int] | None = None
    only_unenriched: bool = True
    overwrite: bool = False


class BatchEnrichResponse(BaseModel):
    total: int
    enriched: int
    failed: int


class MoveBookRequest(BaseModel):
    from_shelf_id: int
    to_shelf_id: int


class BookIdentifier(BaseModel):
    title: str
    author: str


class BulkBookRequest(BaseModel):
    books: list[BookIdentifier]


class BookLookupResult(BaseModel):
    title: str
    author: str
    open_library_key: str | None = None
    cover_url: str | None = None
    isbn: str | None = None
    isbn13: str | None = None
    publisher: str | None = None
    year_published: int | None = None
    page_count: int | None = None
