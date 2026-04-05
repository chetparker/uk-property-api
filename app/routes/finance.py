"""Finance data endpoints."""
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from app.services.finance import fetch_interest_rates, fetch_exchange_rates, fetch_inflation, calculate_mortgage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Finance"])

class RatesRequest(BaseModel):
    months: int = Field(default=12, ge=1, le=120)

class ExchangeRequest(BaseModel):
    base: str = Field(default="GBP", examples=["GBP"])
    targets: list[str] | None = Field(default=None, examples=[["USD", "EUR"]])

class InflationRequest(BaseModel):
    months: int = Field(default=24, ge=1, le=120)

class MortgageRequest(BaseModel):
    property_price: float = Field(..., gt=0, examples=[350000])
    deposit: float = Field(..., ge=0, examples=[35000])
    interest_rate: float = Field(default=4.5, gt=0)
    term_years: int = Field(default=25, ge=1, le=40)
    is_interest_only: bool = Field(default=False)

@router.post("/interest-rates", summary="Bank of England base rate")
async def interest_rates(body: RatesRequest):
    try: return await fetch_interest_rates(body.months)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/exchange-rates", summary="Currency exchange rates")
async def exchange_rates(body: ExchangeRequest):
    try: return await fetch_exchange_rates(body.base, body.targets)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/inflation", summary="UK CPI inflation data")
async def inflation(body: InflationRequest):
    try: return await fetch_inflation(body.months)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/mortgage-calculator", summary="Mortgage payment calculator")
async def mortgage_calc(body: MortgageRequest):
    try: return calculate_mortgage(body.property_price, body.deposit, body.interest_rate, body.term_years, body.is_interest_only)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
