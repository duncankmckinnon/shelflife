# Phase 2: Open Library Enrichment, Shelf Management & Review Improvements

## Context

Phase 1 established full CRUD for books, shelves, reviews, and tags, plus Goodreads CSV import. The Book model already has `description`, `cover_url`, `publisher`, and `page_count` columns but they're only populated if the user provides them manually or if the Goodreads CSV contains them (it usually doesn't for descriptions/covers).

Reviews currently only support per-book listing, and there's no quick way to rate a book without creating a full review, or to check if a book already exists by title.

This phase adds:
- Open Library API integration to automatically fill in book metadata
- Convenience endpoint for moving books between shelves
- Book existence check by title
- Quick rating endpoint
- Global reviews listing with filters

## Changes

### 1. Add `httpx` as a production dependency

**File:** `pyproject.toml`

Move `httpx>=0.27.0` from dev dependencies into main dependencies. It's already used in tests; now the Open Library service needs it at runtime.

### 2. Add Open Library config

**File:** `shelflife/config.py`

```python
OPENLIBRARY_BASE_URL = os.environ.get("SHELFLIFE_OL_BASE_URL", "https://openlibrary.org")
OPENLIBRARY_COVERS_URL = os.environ.get("SHELFLIFE_OL_COVERS_URL", "https://covers.openlibrary.org")
OPENLIBRARY_TIMEOUT = float(os.environ.get("SHELFLIFE_OL_TIMEOUT", "10.0"))
```

### 3. Add `open_library_key` column to Book

**File:** `shelflife/models/book.py` — add column after `goodreads_id`:
```python
open_library_key: Mapped[str | None] = mapped_column(String(50), unique=True)
```

**New migration:** `alembic/versions/YYYY_MM_DD_HHMM-add_open_library_key.py`
- `add_column('books', 'open_library_key', String(50), nullable=True, unique=True)`

**File:** `shelflife/schemas/book.py` — add `open_library_key: str | None` to `BookResponse`

### 4. Create Open Library service

**New file:** `shelflife/services/openlibrary.py`

Pure API client, no database dependency. Returns a dataclass:

```python
@dataclass
class OpenLibraryMetadata:
    open_library_key: str | None = None    # "/works/OL45804W"
    description: str | None = None
    cover_url: str | None = None
    page_count: int | None = None
    publisher: str | None = None
    publish_year: int | None = None
    subjects: list[str]                    # for auto-tagging
```

Three functions:

- **`fetch_metadata(isbn, isbn13, title, author)`** — main entry point, tries ISBN first then title+author search
- **`fetch_metadata_by_isbn(isbn)`** — `GET /isbn/{isbn}.json` for edition data, then `GET /works/{key}.json` for description + subjects. Cover URL built deterministically: `covers.openlibrary.org/b/isbn/{isbn}-L.jpg`
- **`fetch_metadata_by_title_author(title, author)`** — `GET /search.json?title=...&author=...&limit=5`, score results by title/author similarity, fetch work details for best match

Key details:
- Open Library `description` can be a string or `{"type": "...", "value": "string"}` — handle both
- All errors caught and logged, returns `None` on failure (never raises)
- Uses `httpx.AsyncClient` with configurable timeout

### 5. Create enrichment service

**New file:** `shelflife/services/enrich_service.py`

Bridges the API client with the database (same pattern as `import_service.py`):

- **`enrich_book(session, book, overwrite=False)`** — fetches metadata, applies to book fields (only fills blanks unless `overwrite=True`), auto-creates tags from subjects. Returns `EnrichResult` dataclass with `fields_updated` and `tags_added` lists.
- **`enrich_books_batch(session, book_ids=None, only_unenriched=True, overwrite=False)`** — enriches multiple books sequentially (respects Open Library rate limits). Single commit at the end.

### 6. Add enrichment schemas

**File:** `shelflife/schemas/book.py` — add:

```python
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
```

### 7. Add enrichment endpoints

**File:** `shelflife/routers/books.py`

- Modify `create_book` to accept `enrich: bool = Query(False)` — when true, enrich after creation (flush first to get ID, enrich, then commit)
- Add `POST /api/books/{book_id}/enrich` — enrich a single existing book, accepts optional `overwrite` body param

**File:** `shelflife/routers/import_export.py`

- Add `POST /api/import/enrich` — batch enrich endpoint (avoids path conflict with `/{book_id}` on books router)
- Add optional `enrich: bool = Query(False)` to the existing Goodreads import endpoint

### 8. Add book lookup by title

**File:** `shelflife/routers/books.py`

- Add `GET /api/books/search` — accepts `title: str` query param (required), returns matching books. Uses `ilike` for case-insensitive partial matching. Returns `list[BookResponse]`.
- This is distinct from the existing `GET /api/books?q=` in that it's a dedicated existence-check endpoint that requires a title and returns a focused result (useful for "do I already own this?" checks before adding a book).

### 9. Add quick rating and global reviews

**File:** `shelflife/routers/reviews.py`

- Add `PUT /api/books/{book_id}/rating` — accepts `{"rating": 4}` body. If book has an existing review, updates the rating. If not, creates a new review with just the rating (no text). Returns the review.
- Add `GET /api/reviews` — global reviews list with optional filters:
  - `rating: int | None` — filter by exact rating
  - `min_rating: int | None` — filter by minimum rating
  - `limit/offset` — pagination
  - Returns `list[ReviewWithBook]` (review + book title/author for context)

**File:** `shelflife/schemas/review.py` — add:

```python
class RatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)

class ReviewWithBook(ReviewResponse):
    book_title: str
    book_author: str
```

### 10. Add move-book endpoint

**File:** `shelflife/routers/shelves.py`

- Add `POST /api/shelves/move-book/{book_id}` with `MoveBookRequest` body (`from_shelf_id`, `to_shelf_id`)
- Validates book exists, both shelves exist, book is on source shelf, not already on destination
- Atomic: deletes source link, creates destination link preserving `date_added` and `date_read`

### 11. Tests

**New file:** `tests/test_openlibrary.py`
- Unit tests for `_pick_best_match`, `_extract_year` helpers
- Async tests with mocked `httpx` for ISBN lookup, title search, fallback behavior, error handling

**New file:** `tests/test_enrich_api.py`
- Mock `fetch_metadata` at the service level
- Test `POST /api/books/{id}/enrich` enriches and returns updated fields
- Test `POST /api/books?enrich=true` auto-enriches on creation
- Test `POST /api/import/enrich` batch enrichment
- Test graceful failure when Open Library returns nothing

**File:** `tests/test_api.py` — add:
- `test_move_book_between_shelves` — create book + two shelves, add to first, move to second, verify
- `test_search_books_by_title` — create books, search by title, verify partial match
- `test_quick_rating` — rate a book via `PUT /api/books/{id}/rating`, verify review created/updated
- `test_global_reviews_list` — create reviews across books, verify `GET /api/reviews` returns all with book context

### 12. Update docs

**File:** `docs/architecture.md` — add all new endpoints to API tables, move Phase 2 from "Future" to current

## New API endpoints summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/books/search?title=...` | Check if a book exists by title |
| POST | `/api/books?enrich=true` | Create book with optional auto-enrichment |
| POST | `/api/books/{id}/enrich` | Enrich a single book from Open Library |
| PUT | `/api/books/{id}/rating` | Quick-rate a book (1-5), creates/updates review |
| GET | `/api/reviews` | List all reviews with book info, filterable by rating |
| POST | `/api/import/enrich` | Batch enrich books |
| POST | `/api/import/goodreads?enrich=true` | Import with optional enrichment |
| POST | `/api/shelves/move-book/{book_id}` | Move book between shelves |

## Implementation order

| Step | Files | Notes |
|------|-------|-------|
| 1 | `pyproject.toml` | Add httpx to prod deps, run `uv sync` |
| 2 | `config.py` | Open Library settings |
| 3 | `models/book.py`, new migration | `open_library_key` column |
| 4 | `schemas/book.py`, `schemas/review.py` | New fields + enrichment/move/rating schemas |
| 5 | `services/openlibrary.py` (new) | API client |
| 6 | `services/enrich_service.py` (new) | DB enrichment orchestration |
| 7 | `routers/books.py` | Search, enrich on create, single enrich endpoint |
| 8 | `routers/reviews.py` | Quick rating + global reviews list |
| 9 | `routers/import_export.py` | Batch enrich + import enrichment flag |
| 10 | `routers/shelves.py` | Move-book endpoint |
| 11 | Tests | All new test files + additions to `test_api.py` |
| 12 | `docs/architecture.md` | Update API docs |

## Verification

1. `uv run pytest` — all existing + new tests pass
2. `uv run uvicorn shelflife.app:app --reload` — start local server
3. Create a book: `POST /api/books` with `{"title": "Dune", "author": "Frank Herbert", "isbn": "0441172717"}`
4. Search for it: `GET /api/books/search?title=dune` — verify it shows up
5. Quick rate it: `PUT /api/books/1/rating` with `{"rating": 5}` — verify review created
6. List all reviews: `GET /api/reviews` — verify includes book title/author
7. Enrich it: `POST /api/books/1/enrich` — verify description, cover_url, tags populated
8. Check at `GET /api/books/1` — enriched fields visible
9. Test move: create two shelves, add book to first, `POST /api/shelves/move-book/1` — verify it moved
10. `http://localhost:8000/docs` — all new endpoints appear in Swagger
