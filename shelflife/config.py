import os
from pathlib import Path

DB_PATH = os.environ.get("SHELFLIFE_DB_PATH", str(Path.cwd() / "shelflife.db"))
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Open Library API settings
OPENLIBRARY_BASE_URL = os.environ.get("SHELFLIFE_OL_BASE_URL", "https://openlibrary.org")
OPENLIBRARY_COVERS_URL = os.environ.get("SHELFLIFE_OL_COVERS_URL", "https://covers.openlibrary.org")
OPENLIBRARY_TIMEOUT = float(os.environ.get("SHELFLIFE_OL_TIMEOUT", "10.0"))
