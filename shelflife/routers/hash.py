from fastapi import APIRouter, Query

from shelflife.id import make_id
from shelflife.schemas.hash import HashResponse

router = APIRouter(prefix="/api", tags=["hash"])


@router.get("/hash", response_model=HashResponse)
async def compute_hash(
    parts: list[str] = Query(..., description="One or more string parts to hash"),
):
    return HashResponse(id=make_id(*parts), parts=parts)
