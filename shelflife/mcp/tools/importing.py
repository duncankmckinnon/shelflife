from pathlib import Path

from shelflife.mcp.client import ShelflifeClient


async def import_goodreads(
    client: ShelflifeClient,
    file_path: str | None = None,
    csv_content: str | None = None,
) -> dict:
    if file_path:
        p = Path(file_path).expanduser()
        if not p.exists():
            return {"error": True, "detail": f"File not found: {file_path}"}
        csv_content = p.read_text(encoding="utf-8")
    if not csv_content:
        return {"error": True, "detail": "Provide either file_path or csv_content"}
    files = {"file": ("goodreads.csv", csv_content.encode(), "text/csv")}
    return await client.upload("/api/import/goodreads", files=files)
