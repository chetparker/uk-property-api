"""
flood_risk.py — /flood-risk Endpoint
======================================
Returns flood risk assessment for a UK postcode.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

from app.services.flood_risk import fetch_flood_risk
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Property Data"])


class FloodRiskRequest(BaseModel):
    postcode: str = Field(..., description="UK postcode to search", examples=["SW1A 1AA"])


@router.post(
    "/flood-risk",
    summary="Get flood risk assessment for a postcode",
    description=(
        "Checks flood risk from rivers, sea, and surface water for a UK postcode. "
        "Also fetches active flood warnings from the Environment Agency. "
        "Returns overall risk level, detailed breakdown, and insurance guidance."
    ),
)
async def get_flood_risk(body: FloodRiskRequest, request: Request):
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()
    cache_key = make_cache_key("flood-risk", postcode=postcode)
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for flood-risk: {postcode}")
        cached_data["cached"] = True
        return cached_data

    try:
        result = await fetch_flood_risk(postcode)
    except Exception as e:
        logger.error(f"Flood risk query failed for {postcode}: {e}")
        raise HTTPException(status_code=500, detail={"error": "flood_risk_error", "detail": str(e)})

    await cache_set(cache_key, result)
    result["cached"] = False
    return result
