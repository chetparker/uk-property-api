"""
planning.py — /planning Endpoint
==================================
Returns nearby planning applications for a UK postcode.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

from app.services.planning import fetch_planning_applications
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Property Data"])


class PlanningRequest(BaseModel):
    postcode: str = Field(..., description="UK postcode to search", examples=["SW1A 1AA"])
    radius: int = Field(default=500, ge=100, le=5000, description="Search radius in metres")


@router.post(
    "/planning",
    summary="Get planning applications near a postcode",
    description=(
        "Fetches planning applications near a UK postcode from the Planning Data API. "
        "Returns a list of applications with reference, description, status, and date."
    ),
)
async def get_planning(body: PlanningRequest, request: Request):
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()
    cache_key = make_cache_key("planning", postcode=postcode, radius=body.radius)
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for planning: {postcode}")
        cached_data["cached"] = True
        return cached_data

    try:
        result = await fetch_planning_applications(postcode, body.radius)
    except Exception as e:
        logger.error(f"Planning query failed for {postcode}: {e}")
        raise HTTPException(status_code=500, detail={"error": "planning_error", "detail": str(e)})

    await cache_set(cache_key, result)
    result["cached"] = False
    return result
