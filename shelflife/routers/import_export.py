from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from shelflife.database import get_session
from shelflife.schemas.book import BatchEnrichRequest, BatchEnrichResponse
from shelflife.services.enrich_service import enrich_books_batch
from shelflife.services.goodreads import parse_goodreads_csv
from shelflife.services.import_service import import_goodreads_rows

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/goodreads")
async def import_goodreads(
    file: UploadFile,
    enrich: bool = Query(False, description="Enrich imported books with Open Library metadata"),
    session: AsyncSession = Depends(get_session),
):
    content = (await file.read()).decode("utf-8")
    rows = parse_goodreads_csv(content)
    result = await import_goodreads_rows(session, rows)

    response = {
        "books_created": result.books_created,
        "books_updated": result.books_updated,
        "shelves_created": result.shelves_created,
        "reviews_created": result.reviews_created,
        "readings_created": result.readings_created,
    }

    if enrich:
        enrich_result = await enrich_books_batch(session, only_unenriched=True)
        response["enrichment"] = {
            "total": enrich_result.total,
            "enriched": enrich_result.enriched,
            "failed": enrich_result.failed,
        }

    return response


@router.post("/enrich", response_model=BatchEnrichResponse)
async def batch_enrich(
    data: BatchEnrichRequest = BatchEnrichRequest(),
    session: AsyncSession = Depends(get_session),
):
    result = await enrich_books_batch(
        session,
        book_ids=data.book_ids,
        only_unenriched=data.only_unenriched,
        overwrite=data.overwrite,
    )
    return BatchEnrichResponse(
        total=result.total,
        enriched=result.enriched,
        failed=result.failed,
    )
