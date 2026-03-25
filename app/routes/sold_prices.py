"""
sold_prices.py — /sold-prices Endpoint
========================================
Returns recent property sale prices for a UK postcode.
Data comes from HM Land Registry's public SPARQL API.

This file is a "router" — it defines the URL path and HTTP method,
validates the input, calls the service layer, and returns the response.
It does NOT contain business logic (that lives in app/services/).
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import SoldPriceRequest, SoldPriceResponse, ErrorResponse
from app.services.land_registry import fetch_sold_prices
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)

# Create a router. This is like a mini-app that gets plugged into the main app.
# The "tags" group this endpoint in the /docs UI.
router = APIRouter(tags=["Property Data"])


@router.post(
    "/sold-prices",
    response_model=SoldPriceResponse,
    responses={
        402: {"description": "Payment required — see x402 instructions in response body"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Land Registry query failed"},
    },
    summary="Get recent sold prices for a UK postcode",
    description=(
        "Queries HM Land Registry's public database for recent property sales. "
        "Results are cached for 1 hour to reduce latency on repeat lookups. "
        "Returns up to 100 records, ordered by sale date (newest first)."
    ),
)
async def get_sold_prices(body: SoldPriceRequest, request: Request):
    """
    Fetch sold property prices from HM Land Registry.

    **How to use:**
    ```json
    POST /sold-prices
    {
        "postcode": "SW1A 1AA",
        "limit": 10
    }
    ```

    **Caching:** Results are cached for 1 hour. The `cached` field in the
    response tells you whether this was a cache hit.

    **Payment:** This endpoint requires x402 payment. If you call it without
    an X-PAYMENT header, you'll receive a 402 response with payment instructions.
    """
    # --- Rate Limiting ---
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()

    # --- Check Cache ---
    cache_key = make_cache_key("sold-prices", postcode=postcode, limit=body.limit)
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for sold-prices: {postcode}")
        return SoldPriceResponse(
            postcode=postcode,
            count=len(cached_data),
            results=cached_data,
            cached=True,
        )

    # --- Fetch from Land Registry ---
    try:
        records = await fetch_sold_prices(postcode, body.limit)
    except Exception as e:
        logger.error(f"Land Registry query failed for {postcode}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "land_registry_error",
                "detail": (
                    f"Failed to query Land Registry for postcode '{postcode}'. "
                    "This may be a temporary issue — try again in a few seconds."
                ),
            },
        )

    # --- Store in Cache ---
    # Convert records to dicts for JSON serialisation.
    records_as_dicts = [r.model_dump() for r in records]
    await cache_set(cache_key, records_as_dicts)

    return SoldPriceResponse(
        postcode=postcode,
        count=len(records),
        results=records,
        cached=False,
    )
