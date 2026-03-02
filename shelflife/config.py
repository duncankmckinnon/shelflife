import os
from pathlib import Path


def _build_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        # Neon provides postgres:// or postgresql:// — convert to asyncpg driver
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    db_path = os.environ.get("SHELFLIFE_DB_PATH", str(Path.cwd() / "shelflife.db"))
    return f"sqlite+aiosqlite:///{db_path}"


DATABASE_URL = _build_database_url()
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

REMOTE_URL = os.environ.get("SHELFLIFE_REMOTE_URL")
API_KEY = os.environ.get("SHELFLIFE_API_KEY")
SYNC_INTERVAL = int(os.environ.get("SHELFLIFE_SYNC_INTERVAL", "60"))
LOCAL_USERNAME = os.environ.get("SHELFLIFE_LOCAL_USERNAME")

OPENLIBRARY_BASE_URL = os.environ.get("SHELFLIFE_OL_BASE_URL", "https://openlibrary.org")
OPENLIBRARY_COVERS_URL = os.environ.get("SHELFLIFE_OL_COVERS_URL", "https://covers.openlibrary.org")
OPENLIBRARY_TIMEOUT = float(os.environ.get("SHELFLIFE_OL_TIMEOUT", "10.0"))
