"""Weather endpoints."""
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from app.services.weather import fetch_current_weather, fetch_forecast, fetch_historical_weather, fetch_air_quality

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Weather"])

class LocationRequest(BaseModel):
    location: str = Field(..., description="City or place name", examples=["London"])

class ForecastRequest(BaseModel):
    location: str = Field(..., examples=["London"])
    days: int = Field(default=7, ge=1, le=16)

class HistoricalRequest(BaseModel):
    location: str = Field(..., examples=["London"])
    start_date: str = Field(..., examples=["2024-01-01"])
    end_date: str = Field(..., examples=["2024-01-31"])

@router.post("/current-weather", summary="Current weather conditions")
async def current_weather(body: LocationRequest):
    try: return await fetch_current_weather(body.location)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/weather-forecast", summary="Multi-day weather forecast")
async def weather_forecast(body: ForecastRequest):
    try: return await fetch_forecast(body.location, body.days)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/historical-weather", summary="Historical weather data")
async def historical_weather(body: HistoricalRequest):
    try: return await fetch_historical_weather(body.location, body.start_date, body.end_date)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/air-quality", summary="Air quality index")
async def air_quality(body: LocationRequest):
    try: return await fetch_air_quality(body.location)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
