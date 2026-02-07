# Shelflife — Architecture & Plan

## Overview

Shelflife is a personal book management system — a self-hosted alternative to Goodreads.
It stores your books, shelves, reviews, and tags in a local SQLite database, exposes a
REST API for consumption by personal websites and apps, and will eventually include an
MCP server for direct AI integration.

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.12+ | Existing .gitignore setup, ecosystem fit |
| Framework | FastAPI | Modern, async, auto-generates OpenAPI docs |
| Database | SQLite via SQLAlchemy (async) | No server needed, file-based, personal use |
| Async | Yes (aiosqlite) | Idiomatic FastAPI, non-blocking I/O |
| Migrations | Alembic | Standard SQLAlchemy migration tool |
| Validation | Pydantic v2 | Native FastAPI integration |
| Book metadata | Open Library API | Free, no API key, good coverage (future phase) |
| AI interface | MCP Server + REST API | MCP for Claude, REST for websites (future phase) |
| Packaging | Docker Compose | Single container, persistent volume for SQLite |
| License | MIT | |

## Phase 1: Foundation (Current)

### Goals
1. Database schema for books, shelves, reviews, tags
2. Goodreads CSV import to populate from existing library
3. CRUD API endpoints for all entities
4. Docker setup for easy running

### Project Structure

```
shelflife/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── shelflife/
│   ├── __init__.py
│   ├── app.py                  # FastAPI app factory
│   ├── config.py               # Settings (DB path, etc.)
│   ├── database.py             # Engine, async session, Base
│   ├── models/
│   │   ├── __init__.py
│   │   ├── book.py             # Book, BookTag
│   │   ├── shelf.py            # Shelf, ShelfBook
│   │   ├── review.py           # Review
│   │   └── tag.py              # Tag
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── book.py
│   │   ├── shelf.py
│   │   ├── review.py
│   │   └── tag.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── books.py            # /api/books
│   │   ├── shelves.py          # /api/shelves
│   │   ├── reviews.py          # /api/reviews
│   │   ├── tags.py             # /api/tags
│   │   └── import_export.py    # /api/import
│   └── services/
│       ├── __init__.py
│       ├── goodreads.py        # Parse Goodreads CSV export
│       └── import_service.py   # Orchestrate import into DB
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_goodreads_parser.py
│   └── test_api.py
└── docs/
    └── architecture.md         # This file
```

### Data Model

#### Books
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto-increment |
| title | TEXT NOT NULL | |
| author | TEXT NOT NULL | primary author |
| additional_authors | TEXT | comma-separated |
| isbn | TEXT | unique, nullable |
| isbn13 | TEXT | unique, nullable |
| publisher | TEXT | |
| page_count | INTEGER | |
| year_published | INTEGER | |
| description | TEXT | |
| cover_url | TEXT | |
| goodreads_id | TEXT | unique, for dedup on re-import |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto on update |

#### Shelves
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT NOT NULL UNIQUE | e.g. "Read", "Want to Read" |
| description | TEXT | |
| is_exclusive | BOOLEAN | true for read/currently-reading/to-read |
| created_at | DATETIME | |

#### ShelfBooks (association)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| shelf_id | FK -> shelves | |
| book_id | FK -> books | |
| date_added | DATETIME | when added to shelf |
| date_read | DATE | nullable, when finished |
| UNIQUE(shelf_id, book_id) | | prevents duplicates |

#### Reviews
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| book_id | FK -> books | |
| rating | INTEGER | 1-5, nullable (unrated reviews allowed) |
| review_text | TEXT | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### Tags
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT NOT NULL UNIQUE | |

#### BookTags (association)
| Column | Type | Notes |
|--------|------|-------|
| book_id | FK -> books | composite PK |
| tag_id | FK -> tags | composite PK |

### Goodreads CSV Import

Standard Goodreads export columns used:
- `Book Id` -> `goodreads_id` (dedup key)
- `Title`, `Author`, `Additional Authors`
- `ISBN`, `ISBN13` (stripped of `="..."` wrapper)
- `Publisher`, `Number of Pages`, `Year Published`, `Original Publication Year`
- `My Rating` -> Review.rating (if > 0)
- `My Review` -> Review.review_text (if non-empty)
- `Exclusive Shelf` -> Shelf (is_exclusive=true)
- `Bookshelves` -> additional Shelves (comma-separated)
- `Date Added`, `Date Read` -> ShelfBook timestamps

Import is idempotent: re-importing the same CSV updates existing books (matched by `goodreads_id`) rather than creating duplicates.

### API Endpoints

#### Books — `/api/books`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/books` | List books (paginated, filter by author/shelf/tag) |
| GET | `/api/books/{id}` | Book detail with shelves, reviews, tags |
| POST | `/api/books` | Add a book manually |
| PUT | `/api/books/{id}` | Update a book |
| DELETE | `/api/books/{id}` | Delete a book |

#### Shelves — `/api/shelves`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/shelves` | List shelves with book counts |
| GET | `/api/shelves/{id}` | Shelf detail with its books |
| POST | `/api/shelves` | Create a shelf |
| PUT | `/api/shelves/{id}` | Update shelf |
| DELETE | `/api/shelves/{id}` | Delete shelf |
| POST | `/api/shelves/{id}/books/{book_id}` | Add book to shelf |
| DELETE | `/api/shelves/{id}/books/{book_id}` | Remove book from shelf |

#### Reviews — `/api/reviews`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/books/{book_id}/reviews` | Reviews for a book |
| POST | `/api/books/{book_id}/reviews` | Add review |
| PUT | `/api/reviews/{id}` | Update review |
| DELETE | `/api/reviews/{id}` | Delete review |

#### Tags — `/api/tags`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tags` | List all tags |
| POST | `/api/books/{book_id}/tags` | Tag a book |
| DELETE | `/api/books/{book_id}/tags/{tag_id}` | Remove tag |

#### Import — `/api/import`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/import/goodreads` | Upload Goodreads CSV file |

### Docker Setup

Single container running the FastAPI app with uvicorn. SQLite database stored on a
persistent Docker volume.

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - shelflife-data:/data
    environment:
      - SHELFLIFE_DB_PATH=/data/shelflife.db
volumes:
  shelflife-data:
```

### Dependencies

```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
aiosqlite
alembic
pydantic>=2.0
python-multipart
```

Dev dependencies: `pytest`, `pytest-asyncio`, `httpx` (for async test client).

### Implementation Order

| Step | What | Key Files |
|------|------|-----------|
| 1 | Project setup | `pyproject.toml`, `shelflife/config.py` |
| 2 | Database + models | `shelflife/database.py`, `shelflife/models/*` |
| 3 | Alembic init + migration | `alembic.ini`, `alembic/` |
| 4 | Pydantic schemas | `shelflife/schemas/*` |
| 5 | Goodreads parser + import | `shelflife/services/*` |
| 6 | API routers + app | `shelflife/routers/*`, `shelflife/app.py` |
| 7 | Docker | `Dockerfile`, `docker-compose.yml` |
| 8 | Tests | `tests/*` |

### Verification
- `docker compose up --build` starts API on port 8000
- `http://localhost:8000/docs` shows Swagger UI
- Upload Goodreads CSV via `/api/import/goodreads`, verify at `/api/books`
- CRUD operations work via Swagger UI or curl
- `pytest` passes

---

## Future Phases

### Phase 2: Enrichment
- Open Library API integration for metadata, covers, descriptions
- Automatic enrichment on book add / import

### Phase 3: AI Integration
- MCP Server exposing tools: add_book, add_review, move_to_shelf, search, stats
- Reading statistics and recommendations

### Phase 4: Website API
- Public-facing read-only endpoints for personal website
- Currently reading widget, recent reviews, shelf browsing
