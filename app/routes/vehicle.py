"""Vehicle data endpoints."""
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from app.services.vehicle import fetch_vehicle_info, fetch_mot_history, fetch_tax_status, fetch_emissions

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Vehicle Data"])

class VehicleRequest(BaseModel):
    registration: str = Field(..., description="UK registration number", examples=["AB12CDE"])

@router.post("/vehicle-info", summary="Vehicle details")
async def vehicle_info(body: VehicleRequest):
    try: return await fetch_vehicle_info(body.registration)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/mot-history", summary="Full MOT test history")
async def mot_history(body: VehicleRequest):
    try: return await fetch_mot_history(body.registration)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/tax-status", summary="Vehicle tax and MOT status")
async def tax_status(body: VehicleRequest):
    try: return await fetch_tax_status(body.registration)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/emissions", summary="Vehicle emissions data")
async def emissions_data(body: VehicleRequest):
    try: return await fetch_emissions(body.registration)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
