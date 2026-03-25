"""
stamp_duty.py — /stamp-duty Endpoint
======================================
Calculates UK Stamp Duty Land Tax (SDLT) for a property purchase.

This endpoint does NOT require caching or external API calls — it's
pure maths. It's the simplest of the three endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import StampDutyRequest, StampDutyResponse, ErrorResponse
from app.services.sdlt import calculate_sdlt
from app.middleware.rate_limiter import check_rate_limit, extract_wallet_from_request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Property Data"])


@router.post(
    "/stamp-duty",
    response_model=StampDutyResponse,
    responses={
        402: {"description": "Payment required"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Calculate UK Stamp Duty (SDLT)",
    description=(
        "Calculates Stamp Duty Land Tax for England & Northern Ireland. "
        "Supports first-time buyer relief, additional property surcharge "
        "(5% since Oct 2024), and non-resident surcharge (2%). "
        "Returns a full band-by-band breakdown."
    ),
)
async def get_stamp_duty(body: StampDutyRequest, request: Request):
    """
    Calculate stamp duty for a property purchase.

    **How to use:**
    ```json
    POST /stamp-duty
    {
        "price": 350000,
        "is_first_time_buyer": false,
        "is_additional_property": false,
        "is_non_resident": false
    }
    ```

    **Rates as of April 2025 (standard):**
    - £0–£125k: 0%
    - £125k–£250k: 2%
    - £250k–£925k: 5%
    - £925k–£1.5m: 10%
    - Over £1.5m: 12%
    """
    wallet = extract_wallet_from_request(request)
    if wallet:
        await check_rate_limit(wallet)

    try:
        result = calculate_sdlt(
            price=body.price,
            is_first_time_buyer=body.is_first_time_buyer,
            is_additional_property=body.is_additional_property,
            is_non_resident=body.is_non_resident,
        )
    except Exception as e:
        logger.error(f"SDLT calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "calculation_error", "detail": str(e)},
        )

    return StampDutyResponse(
        price=body.price,
        total_tax=result["total_tax"],
        effective_rate=result["effective_rate"],
        breakdown=result["breakdown"],
        buyer_type=result["buyer_type"],
    )
