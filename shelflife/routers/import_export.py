from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.database import get_session
from shelflife.services.goodreads import parse_goodreads_csv
from shelflife.services.import_service import import_goodreads_rows

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/goodreads")
async def import_goodreads(
    file: UploadFile, session: AsyncSession = Depends(get_session)
):
    content = (await file.read()).decode("utf-8")
    rows = parse_goodreads_csv(content)
    result = await import_goodreads_rows(session, rows)
    return {
        "books_created": result.books_created,
        "books_updated": result.books_updated,
        "shelves_created": result.shelves_created,
        "reviews_created": result.reviews_created,
    }
