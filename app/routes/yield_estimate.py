"""
yield_estimate.py — /yield-estimate Endpoint
==============================================
Estimates the gross rental yield for a UK postcode.

Uses regional rental benchmarks (from ONS data) and optionally fetches
the average sold price from Land Registry if no property value is provided.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import YieldRequest, YieldResponse, ErrorResponse
from app.services.voa_rental import calculate_yield
from app.services.land_registry import fetch_sold_prices
from app.middleware.cache import cache_get, cache_set, make_cache_key
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Property Data"])


@router.post(
    "/yield-estimate",
    response_model=YieldResponse,
    responses={
        402: {"description": "Payment required"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Calculation failed"},
    },
    summary="Estimate gross rental yield for a UK postcode",
    description=(
        "Calculates estimated gross rental yield using regional rental data. "
        "If no property_value is provided, the API fetches the average recent "
        "sold price from Land Registry as a baseline. Results are cached."
    ),
)
async def get_yield_estimate(body: YieldRequest, request: Request):
    """
    Estimate rental yield for a UK postcode.

    **How to use:**
    ```json
    POST /yield-estimate
    {
        "postcode": "M1 1AA",
        "property_value": 250000
    }
    ```

    If you omit `property_value`, the API will look up recent sold prices
    and use the average as the property value.
    """
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    postcode = body.postcode.strip().upper()
    property_value = body.property_value

    # --- Check Cache ---
    cache_key = make_cache_key(
        "yield", postcode=postcode, value=str(property_value or "auto")
    )
    cached_data = await cache_get(cache_key)

    if cached_data is not None:
        logger.info(f"Cache hit for yield-estimate: {postcode}")
        cached_data["cached"] = True
        return YieldResponse(**cached_data)

    # --- Resolve property value if not provided ---
    if property_value is None:
        try:
            # Fetch recent sold prices to calculate an average.
            records = await fetch_sold_prices(postcode, limit=20)
            if records:
                # Use the average of recent sale prices.
                prices = [r.price for r in records]
                property_value = sum(prices) / len(prices)
                logger.info(
                    f"Auto-resolved property value for {postcode}: "
                    f"£{property_value:,.0f} (avg of {len(prices)} sales)"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": "no_data",
                        "detail": (
                            f"No sold price data found for postcode '{postcode}'. "
                            "Please provide a property_value manually."
                        ),
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to auto-resolve property value: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "lookup_failed",
                    "detail": (
                        "Could not auto-resolve property value from Land Registry. "
                        "Please provide a property_value in your request."
                    ),
                },
            )

    # --- Calculate Yield ---
    try:
        result = calculate_yield(postcode=postcode, property_value=property_value)
    except Exception as e:
        logger.error(f"Yield calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "calculation_error", "detail": str(e)},
        )

    # --- Store in Cache ---
    await cache_set(cache_key, result)

    return YieldResponse(**result, cached=False)
