"""
council_tax.py — /council-tax Endpoint
========================================
Returns council tax bands and estimated annual bills for a UK postcode.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

from app.services.council_tax import fetch_council_tax
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Property Data"])


class CouncilTaxRequest(BaseModel):
    postcode: str = Field(..., description="UK postcode to search", examples=["SW1A 1AA"])


@router.post(
    "/council-tax",
    summary="Get council tax estimates for a postcode",
    description=(
        "Looks up the local authority for a UK postcode and calculates estimated "
        "council tax for all bands A-H using statutory multipliers. "
        "Uses known Band D rates for ~60 major authorities with a national average fallback."
    ),
)
async def get_council_tax(body: CouncilTaxRequest, request: Request):
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()
    cache_key = make_cache_key("council-tax", postcode=postcode)
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for council-tax: {postcode}")
        cached_data["cached"] = True
        return cached_data

    try:
        result = await fetch_council_tax(postcode)
    except Exception as e:
        logger.error(f"Council tax query failed for {postcode}: {e}")
        raise HTTPException(status_code=500, detail={"error": "council_tax_error", "detail": str(e)})

    await cache_set(cache_key, result)
    result["cached"] = False
    return result
