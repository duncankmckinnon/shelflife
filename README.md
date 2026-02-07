# Shelflife

A self-hosted personal book management system — an alternative to Goodreads that you own and control.

Shelflife stores your books, shelves, reviews, and tags in a local SQLite database and exposes a REST API for consumption by personal websites, apps, and AI assistants. Import your existing Goodreads library with a single CSV upload.

## Why

Goodreads hasn't meaningfully changed in years. Your reading data is locked inside Amazon's ecosystem with no real API access. Shelflife gives you:

- **Full ownership** of your reading data in a portable SQLite file
- **A real API** for building personal dashboards, widgets, and integrations
- **Easy import** from Goodreads CSV exports (idempotent — safe to re-run)
- **Simple deployment** via Docker with persistent storage
- **AI-ready architecture** with a planned MCP server for Claude integration

## Quickstart

### Docker (recommended)

```bash
docker compose up --build
```

The API is available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Local development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn shelflife.app:app --reload
```

### Run tests

```bash
uv run pytest
```

## Importing from Goodreads

1. Go to [Goodreads export](https://www.goodreads.com/review/import) and click "Export Library"
2. Upload the CSV:

```bash
curl -X POST http://localhost:8000/api/import/goodreads \
  -F "file=@goodreads_library_export.csv"
```

The import is idempotent: books are matched by Goodreads ID, so re-importing updates existing records rather than creating duplicates. Shelves, reviews, ratings, and tags are all preserved.

## API

All endpoints are documented via OpenAPI at `/docs`. Here's the overview:

| Resource | Endpoints | Description |
|----------|-----------|-------------|
| Books | `GET/POST /api/books`, `GET/PUT/DELETE /api/books/{id}` | Full CRUD with search, filtering by author/tag, pagination |
| Shelves | `GET/POST /api/shelves`, `GET/PUT/DELETE /api/shelves/{id}` | Organize books into shelves (supports exclusive shelves like "read", "currently-reading") |
| Shelf books | `POST/DELETE /api/shelves/{id}/books/{book_id}` | Add/remove books from shelves |
| Reviews | `GET/POST /api/books/{id}/reviews`, `PUT/DELETE /api/reviews/{id}` | Ratings (1-5) and review text per book |
| Tags | `GET /api/tags`, `POST/DELETE /api/books/{id}/tags/{tag_id}` | Flexible tagging system |
| Import | `POST /api/import/goodreads` | Goodreads CSV upload |

## Tech stack

| Component | Choice | Why |
|-----------|--------|-----|
| Framework | FastAPI | Async, auto-generated OpenAPI docs, Pydantic validation |
| Database | SQLite + SQLAlchemy 2.0 (async) | No server to manage, file-based, perfect for personal use |
| Migrations | Alembic | Schema versioning with timestamp-based naming |
| Validation | Pydantic v2 | Native FastAPI integration, strict type checking |
| Containerization | Docker Compose | Single container, persistent volume for the database |

## Roadmap

Shelflife is built in phases. Phase 1 is complete.

### Phase 1: Foundation (done)
- SQLite database with books, shelves, reviews, and tags
- Goodreads CSV import
- Full CRUD REST API
- Docker deployment

### Phase 2: Enrichment
- Open Library API integration for covers, descriptions, and metadata
- Automatic enrichment on book add and import

### Phase 3: AI Integration
- MCP server exposing tools for Claude: add books, write reviews, manage shelves, get reading stats
- Reading statistics and recommendations

### Phase 4: Website API
- Public-facing read-only endpoints for personal websites
- "Currently reading" widget, recent reviews, shelf browsing

## Project structure

```
shelflife/
├── shelflife/
│   ├── app.py                  # FastAPI application
│   ├── config.py               # Settings (DB path)
│   ├── database.py             # SQLAlchemy async engine + session
│   ├── models/                 # ORM models (book, shelf, review, tag)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── routers/                # API route handlers
│   └── services/               # Business logic (Goodreads parser, import)
├── alembic/                    # Database migrations
├── tests/                      # pytest suite
├── Dockerfile
├── docker-compose.yml
└── docs/
    └── architecture.md         # Detailed architecture and decisions
```

## License

MIT
