"""
schemas.py — Data Models (Shapes)
==================================
These Pydantic models define the exact shape of data going in and out of the API.

WHY BOTHER?
    1. Validation — FastAPI auto-rejects requests that don't match these shapes.
    2. Documentation — These models auto-generate the OpenAPI schema at /docs.
    3. Type safety — Your editor can autocomplete fields and catch typos.

HOW TO READ THIS:
    Each class is like a form template. The fields are the form's boxes.
    `str` means text, `float` means a decimal number, `int` means a whole number.
    `Optional` means the field can be left blank.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# =============================================================================
# /sold-prices
# =============================================================================

class SoldPriceRequest(BaseModel):
    """
    What the caller sends to /sold-prices.
    Example: {"postcode": "SW1A 1AA", "limit": 10}
    """
    postcode: str = Field(
        ...,                              # "..." means this field is REQUIRED
        description="UK postcode to search, e.g. 'SW1A 1AA'",
        examples=["SW1A 1AA"],
    )
    limit: int = Field(
        default=10,                       # Optional — defaults to 10 results
        ge=1,                             # Must be >= 1
        le=100,                           # Must be <= 100
        description="Maximum number of results to return (1–100)",
    )


class SoldPriceRecord(BaseModel):
    """
    One sold-price record returned from HM Land Registry.
    """
    address: str = Field(description="Full property address")
    price: int = Field(description="Sale price in GBP (pounds)")
    date: str = Field(description="Date of sale (YYYY-MM-DD)")
    property_type: str = Field(description="Type: Detached, Semi, Terraced, Flat")
    new_build: bool = Field(description="Whether the property was a new build")


class SoldPriceResponse(BaseModel):
    """
    Full response from /sold-prices.
    """
    postcode: str = Field(description="The postcode that was searched")
    count: int = Field(description="Number of results returned")
    results: list[SoldPriceRecord] = Field(description="List of sold price records")
    cached: bool = Field(
        default=False,
        description="True if this result came from cache (faster, free)"
    )


# =============================================================================
# /yield-estimate
# =============================================================================

class YieldRequest(BaseModel):
    """
    What the caller sends to /yield-estimate.
    Example: {"postcode": "M1 1AA", "property_value": 250000}
    """
    postcode: str = Field(
        ...,
        description="UK postcode for the rental estimate",
        examples=["M1 1AA"],
    )
    property_value: Optional[float] = Field(
        default=None,
        gt=0,                             # Must be greater than 0
        description=(
            "Property value in GBP. If omitted, the API uses the average "
            "sold price from Land Registry for this postcode."
        ),
    )


class YieldResponse(BaseModel):
    """
    Full response from /yield-estimate.
    """
    postcode: str
    estimated_monthly_rent: float = Field(description="Estimated rent in GBP/month")
    estimated_annual_rent: float = Field(description="Estimated rent in GBP/year")
    property_value: float = Field(description="Property value used for calculation")
    gross_yield_percent: float = Field(description="Gross rental yield as a percentage")
    yield_band: str = Field(
        description="Human-readable label: 'Low' (<4%), 'Average' (4-6%), 'High' (>6%)"
    )
    cached: bool = False


# =============================================================================
# /stamp-duty
# =============================================================================

class StampDutyRequest(BaseModel):
    """
    What the caller sends to /stamp-duty.
    Example: {"price": 350000, "is_first_time_buyer": true}
    """
    price: float = Field(
        ...,
        gt=0,
        description="Property purchase price in GBP",
        examples=[350000],
    )
    is_first_time_buyer: bool = Field(
        default=False,
        description="First-time buyers get a discount on properties up to £625,000",
    )
    is_additional_property: bool = Field(
        default=False,
        description="Second homes / buy-to-let pay a 5% surcharge (since Oct 2024)",
    )
    is_non_resident: bool = Field(
        default=False,
        description="Non-UK residents pay an extra 2% surcharge",
    )


class StampDutyBand(BaseModel):
    """
    One row in the stamp duty breakdown table.
    """
    band: str = Field(description="e.g. '£0 – £250,000'")
    rate: str = Field(description="e.g. '0%'")
    tax: float = Field(description="Tax due for this band in GBP")


class StampDutyResponse(BaseModel):
    """
    Full response from /stamp-duty.
    """
    price: float = Field(description="The purchase price used")
    total_tax: float = Field(description="Total SDLT payable in GBP")
    effective_rate: float = Field(description="Effective tax rate as a percentage")
    breakdown: list[StampDutyBand] = Field(description="Tax breakdown by band")
    buyer_type: str = Field(
        description="Summary: 'First-time buyer', 'Standard', 'Additional property', etc."
    )


# =============================================================================
# Error / generic responses
# =============================================================================

class ErrorResponse(BaseModel):
    """
    Returned when something goes wrong (4xx or 5xx status codes).
    """
    error: str = Field(description="Machine-readable error code, e.g. 'rate_limited'")
    detail: str = Field(description="Human-readable explanation")


class HealthResponse(BaseModel):
    """
    Returned by the /health endpoint for uptime monitoring.
    """
    status: str = Field(default="ok")
    version: str
    redis_connected: bool
