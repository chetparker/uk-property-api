"""
epc.py — /epc-rating Endpoint
================================
Returns EPC energy performance data for a UK postcode.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

from app.services.epc import fetch_epc_data
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Property Data"])


class EPCRequest(BaseModel):
    postcode: str = Field(..., description="UK postcode to search", examples=["SW1A 1AA"])
    limit: int = Field(default=20, ge=1, le=100, description="Max certificates to return")


@router.post(
    "/epc-rating",
    summary="Get EPC energy ratings for a postcode",
    description=(
        "Fetches Energy Performance Certificate data for properties at a UK postcode. "
        "Returns individual certificates, average score/band, and band distribution. "
        "Falls back to national average estimates if no EPC API key is configured."
    ),
)
async def get_epc_rating(body: EPCRequest, request: Request):
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()
    cache_key = make_cache_key("epc", postcode=postcode, limit=body.limit)
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for epc: {postcode}")
        cached_data["cached"] = True
        return cached_data

    try:
        result = await fetch_epc_data(postcode, body.limit)
    except Exception as e:
        logger.error(f"EPC query failed for {postcode}: {e}")
        raise HTTPException(status_code=500, detail={"error": "epc_error", "detail": str(e)})

    await cache_set(cache_key, result)
    result["cached"] = False
    return result
