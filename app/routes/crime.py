"""
crime.py — /crime-stats Endpoint
==================================
Returns street-level crime statistics for a UK postcode.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

from app.services.crime import fetch_crime_data
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Property Data"])


class CrimeRequest(BaseModel):
    postcode: str = Field(..., description="UK postcode to search", examples=["SW1A 1AA"])


@router.post(
    "/crime-stats",
    summary="Get street-level crime stats for a postcode",
    description=(
        "Fetches recent street-level crime data from the Police UK API. "
        "Returns total crime count, breakdown by category, and a safety rating (1-5 scale)."
    ),
)
async def get_crime_stats(body: CrimeRequest, request: Request):
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()
    cache_key = make_cache_key("crime", postcode=postcode)
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for crime: {postcode}")
        cached_data["cached"] = True
        return cached_data

    try:
        result = await fetch_crime_data(postcode)
    except Exception as e:
        logger.error(f"Crime query failed for {postcode}: {e}")
        raise HTTPException(status_code=500, detail={"error": "crime_error", "detail": str(e)})

    await cache_set(cache_key, result)
    result["cached"] = False
    return result
