from shelflife.mcp.client import ShelflifeClient


async def import_goodreads(
    client: ShelflifeClient,
    csv_content: str,
) -> dict:
    files = {"file": ("goodreads.csv", csv_content.encode(), "text/csv")}
    return await client.upload("/api/import/goodreads", files=files)
