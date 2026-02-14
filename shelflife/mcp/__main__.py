import os
import subprocess
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from shelflife.app import create_app
from shelflife.mcp.client import ShelflifeClient
from shelflife.mcp.server import create_mcp_server


def run_migrations():
    """Run Alembic migrations before starting the MCP server."""
    # Ensure the database directory exists
    db_path = os.environ.get("SHELFLIFE_DB_PATH", "shelflife.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(1)


def main():
    run_migrations()

    app = create_app()
    transport = ASGITransport(app=app)
    http = AsyncClient(transport=transport, base_url="http://localhost")
    client = ShelflifeClient(http)
    mcp = create_mcp_server(client)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
