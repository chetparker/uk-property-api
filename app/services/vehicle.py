"""UK vehicle data from DVLA/DVSA (free API keys required)."""
import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
DVLA_URL = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"
MOT_URL = "https://beta.check-mot.service.gov.uk/trade/vehicles/mot-tests"


async def fetch_vehicle_info(registration: str) -> dict:
    settings = get_settings()
    reg = registration.upper().replace(" ", "")
    key = getattr(settings, "dvla_api_key", "")
    if not key:
        return {"registration": reg, "make": "FORD", "model": "FOCUS", "colour": "BLUE", "fuel_type": "PETROL", "year": 2019, "co2": 128, "tax_status": "Taxed", "mot_status": "Valid", "note": "Mock data - set DVLA_API_KEY"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(DVLA_URL, json={"registrationNumber": reg}, headers={"x-api-key": key, "Content-Type": "application/json"})
        resp.raise_for_status()
        d = resp.json()
    return {"registration": reg, "make": d.get("make"), "model": d.get("model"), "colour": d.get("colour"), "fuel_type": d.get("fuelType"),
            "year": d.get("yearOfManufacture"), "engine_cc": d.get("engineCapacity"), "co2": d.get("co2Emissions"),
            "tax_status": d.get("taxStatus"), "tax_due": d.get("taxDueDate"), "mot_status": d.get("motStatus"), "mot_expiry": d.get("motExpiryDate")}


async def fetch_mot_history(registration: str) -> dict:
    settings = get_settings()
    reg = registration.upper().replace(" ", "")
    key = getattr(settings, "mot_api_key", "")
    if not key:
        return {"registration": reg, "total_tests": 1, "tests": [{"date": "2024-06-10", "result": "PASSED", "odometer": "45230 mi", "defects": []}], "note": "Mock data - set MOT_API_KEY"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(MOT_URL, params={"registration": reg}, headers={"x-api-key": key, "Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
    if not data:
        return {"registration": reg, "total_tests": 0, "tests": []}
    v = data[0] if isinstance(data, list) else data
    tests = []
    for t in v.get("motTests", []):
        tests.append({"date": t.get("completedDate"), "expiry": t.get("expiryDate"), "result": t.get("testResult"),
                       "odometer": f"{t.get('odometerValue', '')} {t.get('odometerUnit', '')}", "defects": [d.get("text") for d in t.get("defects", [])]})
    return {"registration": reg, "make": v.get("make"), "model": v.get("model"), "total_tests": len(tests), "tests": tests}


async def fetch_tax_status(registration: str) -> dict:
    info = await fetch_vehicle_info(registration)
    return {"registration": info.get("registration"), "make": info.get("make"), "model": info.get("model"),
            "tax_status": info.get("tax_status"), "tax_due": info.get("tax_due"), "mot_status": info.get("mot_status"), "mot_expiry": info.get("mot_expiry")}


async def fetch_emissions(registration: str) -> dict:
    info = await fetch_vehicle_info(registration)
    return {"registration": info.get("registration"), "make": info.get("make"), "model": info.get("model"),
            "fuel_type": info.get("fuel_type"), "engine_cc": info.get("engine_cc"), "co2": info.get("co2"), "year": info.get("year")}
