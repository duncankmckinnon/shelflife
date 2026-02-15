# Shelflife

A self-hosted personal book management system — an alternative to Goodreads that you own and control.

Shelflife stores your books, shelves, reviews, and tags in a local SQLite database and exposes a REST API for consumption by personal websites, apps, and AI assistants. Import your existing Goodreads library with a single CSV upload, then enrich your books with metadata from Open Library.

## Why

Goodreads hasn't meaningfully changed in years. Your reading data is locked inside Amazon's ecosystem with no real API access. Shelflife gives you:

- **Full ownership** of your reading data in a portable SQLite file
- **A real API** for building personal dashboards, widgets, and integrations
- **Easy import** from Goodreads CSV exports (idempotent — safe to re-run)
- **Automatic enrichment** via Open Library for descriptions, covers, and subjects
- **Simple deployment** via Docker with persistent storage
- **Claude integration** via MCP server — manage your library through natural conversation

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

## MCP Server (Claude integration)

Shelflife includes an MCP server that lets Claude manage your reading library through natural conversation — adding books, organizing shelves, writing reviews, tagging, and more.

### With Docker (recommended)

Build the image:

```bash
docker build -t shelflife-mcp --build-arg MODE=mcp .
```

Add to your Claude config:

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "shelflife": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "shelflife-data:/app/data",
        "-e", "SHELFLIFE_DB_PATH=/app/data/shelflife.db",
        "shelflife-mcp"
      ]
    }
  }
}
```

### Available tools

| Tool | Description |
|------|-------------|
| `search_books` | Search by title, author, tag, or free text |
| `get_book` | Get full details including tags, shelves, and review |
| `add_book` | Add a book (auto-enriches from Open Library) |
| `resolve_book` | Enrich an existing book with Open Library metadata |
| `shelve_book` | Place a book on a shelf (creates shelf if needed) |
| `browse_shelf` | List all shelves or browse a specific shelf |
| `review_book` | Rate and/or review a book (1-5 stars) |
| `get_reviews` | List reviews, optionally filtered by rating |
| `tag_books` | Apply a tag to one or more books |
| `browse_tag` | List all tags or get books with a specific tag |
| `reading_profile` | Overview of your reading: stats, top tags, ratings |
| `start_reading` | Start reading a book (tracks start date) |
| `finish_reading` | Finish the active reading of a book |
| `log_reading_progress` | Log progress by page, pages read, or page range |
| `get_reading_history` | Get all readings of a book including re-reads |
| `import_goodreads` | Import a Goodreads CSV export |

## Importing from Goodreads

1. Go to [Goodreads export](https://www.goodreads.com/review/import) and click "Export Library"
2. Upload the CSV:

```bash
curl -X POST http://*server*/api/import/goodreads \
  -F "file=goodreads_library_export.csv"
```

The import is idempotent: books are matched by Goodreads ID, so re-importing updates existing records rather than creating duplicates. Shelves, reviews, ratings, and tags are all preserved.

Add `?enrich=true` to automatically fetch descriptions, covers, and subjects from Open Library during import.

## Enriching books with Open Library

Shelflife integrates with the [Open Library API](https://openlibrary.org/developers/api) to fill in metadata that Goodreads doesn't export (descriptions, cover images, subjects). No API key required.

```bash
# Enrich a single book
curl -X POST http://*server*/api/books/1/enrich

# Batch enrich all unenriched books
curl -X POST http://*server*/api/import/enrich -H 'Content-Type: application/json' -d '{}'

# Create a book with auto-enrichment
curl -X POST 'http://*server*/api/books?enrich=true' \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert"}'
```

Enrichment looks up books by ISBN first (most reliable), then falls back to title+author search. It fills in blank fields without overwriting your data unless you pass `?overwrite=true`. Subjects from Open Library are automatically added as tags.

## API

All endpoints are documented via OpenAPI at `/docs`. Here's the overview:

| Resource | Endpoints | Description |
|----------|-----------|-------------|
| Books | `GET/POST /api/books`, `GET/PUT/DELETE /api/books/{id}` | Full CRUD with search, filtering by author/tag, pagination |
| Book search | `GET /api/books/search?title=...` | Check if a book exists in your library by title |
| Enrichment | `POST /api/books/{id}/enrich` | Fetch metadata from Open Library for a single book |
| Shelves | `GET/POST /api/shelves`, `GET/PUT/DELETE /api/shelves/{id}` | Organize books into shelves (supports exclusive shelves like "read", "currently-reading") |
| Shelf books | `POST/DELETE /api/shelves/{id}/books/{book_id}` | Add/remove books from shelves |
| Move book | `POST /api/shelves/move-book/{book_id}` | Move a book between shelves atomically |
| Reviews | `GET/POST /api/books/{id}/reviews`, `PUT/DELETE /api/reviews/{id}` | Ratings (1-5) and review text per book |
| Quick rate | `PUT /api/books/{id}/rating` | Set a book's rating without writing a full review |
| All reviews | `GET /api/reviews` | Browse all reviews with book context, filter by rating |
| Reading | `POST /api/books/{id}/start-reading`, `PUT /api/books/{id}/finish-reading` | Track reading sessions with start/finish dates, supports re-reads |
| Reading progress | `POST/GET /api/books/{id}/reading/progress` | Log progress by absolute page, pages read, or page range |
| Tags | `GET /api/tags`, `POST/DELETE /api/books/{id}/tags/{tag_id}` | Flexible tagging system |
| Import | `POST /api/import/goodreads` | Goodreads CSV upload (with optional `?enrich=true`) |
| Batch enrich | `POST /api/import/enrich` | Enrich multiple books from Open Library |

## Tech stack

| Component | Choice | Why |
|-----------|--------|-----|
| Framework | FastAPI | Async, auto-generated OpenAPI docs, Pydantic validation |
| Database | SQLite + SQLAlchemy 2.0 (async) | No server to manage, file-based, perfect for personal use |
| Migrations | Alembic | Schema versioning with timestamp-based naming |
| Validation | Pydantic v2 | Native FastAPI integration, strict type checking |
| HTTP client | httpx | Async requests to Open Library API |
| MCP server | FastMCP | Stdio transport, wraps the API in-process via ASGI |
| Containerization | Docker Compose | Single container, persistent volume for the database |

## License

MIT
