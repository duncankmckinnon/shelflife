import os
from pathlib import Path

DB_PATH = os.environ.get("SHELFLIFE_DB_PATH", str(Path.cwd() / "shelflife.db"))
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
