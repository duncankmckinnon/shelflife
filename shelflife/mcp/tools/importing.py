from pathlib import Path

from shelflife.mcp.client import ShelflifeClient


async def _upload_csv(client: ShelflifeClient, csv_content: str) -> dict:
    files = {"file": ("goodreads.csv", csv_content.encode(), "text/csv")}
    return await client.upload("/api/import/goodreads", files=files)


async def import_goodreads(
    client: ShelflifeClient,
    file_path: str,
) -> dict:
    p = Path(file_path).expanduser()
    if not p.exists():
        return {"error": True, "detail": f"File not found: {file_path}"}
    csv_content = p.read_text(encoding="utf-8")
    return await _upload_csv(client, csv_content)


async def import_goodreads_csv(
    client: ShelflifeClient,
    csv_content: str,
) -> dict:
    return await _upload_csv(client, csv_content)
