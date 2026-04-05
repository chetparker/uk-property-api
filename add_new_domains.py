"""
Run this script from the uk-property-api directory to add
weather, company, vehicle, and finance endpoints.

Usage:
    cd ~/Downloads/uk-property-api
    python add_new_domains.py
"""

import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
SERVICES_DIR = os.path.join(BASE, "app", "services")
ROUTES_DIR = os.path.join(BASE, "app", "routes")

# ============================================================
# WEATHER SERVICE
# ============================================================

weather_service = '''"""Weather data from Open-Meteo (free, no API key)."""
import httpx
import logging

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


async def geocode(location: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(GEOCODE_URL, params={"name": location, "count": 1})
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            raise ValueError(f"Location not found: {location}")
        r = results[0]
        return {"name": r["name"], "country": r.get("country", ""), "latitude": r["latitude"], "longitude": r["longitude"]}


async def fetch_current_weather(location: str) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"],
              "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
              "timezone": "auto"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
    c = resp.json().get("current", {})
    return {"location": geo, "current": {
        "temperature_c": c.get("temperature_2m"), "feels_like_c": c.get("apparent_temperature"),
        "humidity_pct": c.get("relative_humidity_2m"), "precipitation_mm": c.get("precipitation"),
        "wind_speed_kmh": c.get("wind_speed_10m"), "weather_code": c.get("weather_code"),
        "description": WMO_CODES.get(c.get("weather_code", 0), "Unknown"), "time": c.get("time"),
    }}


async def fetch_forecast(location: str, days: int = 7) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"],
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,sunrise,sunset",
              "timezone": "auto", "forecast_days": min(days, 16)}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
    d = resp.json().get("daily", {})
    forecast = []
    for i, date in enumerate(d.get("time", [])):
        forecast.append({"date": date, "temp_max_c": d["temperature_2m_max"][i], "temp_min_c": d["temperature_2m_min"][i],
                         "precipitation_mm": d["precipitation_sum"][i], "weather_code": d["weather_code"][i],
                         "description": WMO_CODES.get(d["weather_code"][i], "Unknown"),
                         "sunrise": d["sunrise"][i], "sunset": d["sunset"][i]})
    return {"location": geo, "days": len(forecast), "forecast": forecast}


async def fetch_historical_weather(location: str, start_date: str, end_date: str) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"], "start_date": start_date, "end_date": end_date,
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code", "timezone": "auto"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(ARCHIVE_URL, params=params)
        resp.raise_for_status()
    d = resp.json().get("daily", {})
    history = []
    for i, date in enumerate(d.get("time", [])):
        history.append({"date": date, "temp_max_c": d["temperature_2m_max"][i], "temp_min_c": d["temperature_2m_min"][i],
                         "precipitation_mm": d["precipitation_sum"][i], "description": WMO_CODES.get(d["weather_code"][i], "Unknown")})
    return {"location": geo, "days": len(history), "history": history}


async def fetch_air_quality(location: str) -> dict:
    geo = await geocode(location)
    params = {"latitude": geo["latitude"], "longitude": geo["longitude"],
              "current": "european_aqi,us_aqi,pm10,pm2_5,nitrogen_dioxide,ozone"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(AIR_URL, params=params)
        resp.raise_for_status()
    c = resp.json().get("current", {})
    aqi = c.get("us_aqi", 0)
    cat = "Good" if aqi <= 50 else "Moderate" if aqi <= 100 else "Unhealthy for Sensitive" if aqi <= 150 else "Unhealthy" if aqi <= 200 else "Very Unhealthy" if aqi <= 300 else "Hazardous"
    return {"location": geo, "air_quality": {"us_aqi": aqi, "category": cat, "european_aqi": c.get("european_aqi"),
            "pm10": c.get("pm10"), "pm2_5": c.get("pm2_5"), "nitrogen_dioxide": c.get("nitrogen_dioxide"), "ozone": c.get("ozone")}}
'''

# ============================================================
# COMPANY SERVICE
# ============================================================

company_service = '''"""UK company data from Companies House (free API key required)."""
import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
BASE_URL = "https://api.company-information.service.gov.uk"


def _auth():
    settings = get_settings()
    key = getattr(settings, "companies_house_api_key", "")
    return (key, "") if key else None


async def search_companies(query: str, limit: int = 10) -> dict:
    auth = _auth()
    if not auth:
        return {"query": query, "total_results": 1, "results": [{"company_number": "00000001", "title": f"EXAMPLE {query.upper()} LTD", "company_status": "active", "date_of_creation": "2020-01-15", "address": "1 Example Street, London"}], "note": "Mock data - set COMPANIES_HOUSE_API_KEY"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/search/companies", params={"q": query, "items_per_page": min(limit, 50)}, auth=auth)
        resp.raise_for_status()
        data = resp.json()
    return {"query": query, "total_results": data.get("total_results", 0),
            "results": [{"company_number": i.get("company_number"), "title": i.get("title"), "company_status": i.get("company_status"), "date_of_creation": i.get("date_of_creation"), "address": i.get("address_snippet")} for i in data.get("items", [])]}


async def get_company_profile(company_number: str) -> dict:
    auth = _auth()
    if not auth:
        return {"company_number": company_number, "company_name": "EXAMPLE LTD", "company_status": "active", "sic_codes": ["62012"], "note": "Mock data - set COMPANIES_HOUSE_API_KEY"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/company/{company_number}", auth=auth)
        resp.raise_for_status()
        d = resp.json()
    return {"company_number": d.get("company_number"), "company_name": d.get("company_name"), "company_status": d.get("company_status"),
            "type": d.get("type"), "date_of_creation": d.get("date_of_creation"), "registered_office": d.get("registered_office_address"),
            "sic_codes": d.get("sic_codes", []), "has_charges": d.get("has_charges"), "has_insolvency_history": d.get("has_insolvency_history")}


async def get_officers(company_number: str) -> dict:
    auth = _auth()
    if not auth:
        return {"company_number": company_number, "total_results": 1, "officers": [{"name": "SMITH, John", "officer_role": "director", "appointed_on": "2020-01-15"}], "note": "Mock data"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/company/{company_number}/officers", auth=auth)
        resp.raise_for_status()
        data = resp.json()
    return {"company_number": company_number, "total_results": data.get("total_results", 0),
            "officers": [{"name": i.get("name"), "officer_role": i.get("officer_role"), "appointed_on": i.get("appointed_on"), "resigned_on": i.get("resigned_on")} for i in data.get("items", [])]}


async def get_filing_history(company_number: str, limit: int = 20) -> dict:
    auth = _auth()
    if not auth:
        return {"company_number": company_number, "total_count": 1, "filings": [{"date": "2024-01-15", "type": "AA", "category": "accounts"}], "note": "Mock data"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/company/{company_number}/filing-history", params={"items_per_page": min(limit, 50)}, auth=auth)
        resp.raise_for_status()
        data = resp.json()
    return {"company_number": company_number, "total_count": data.get("total_count", 0),
            "filings": [{"date": i.get("date"), "type": i.get("type"), "category": i.get("category"), "description": i.get("description")} for i in data.get("items", [])]}
'''

# ============================================================
# VEHICLE SERVICE
# ============================================================

vehicle_service = '''"""UK vehicle data from DVLA/DVSA (free API keys required)."""
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
'''

# ============================================================
# FINANCE SERVICE
# ============================================================

finance_service = '''"""UK finance data from Bank of England + ECB (free, no API key)."""
import httpx
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
BOE_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
FX_URL = "https://api.frankfurter.app"


async def fetch_interest_rates(months: int = 12) -> dict:
    end = datetime.now()
    start = end - timedelta(days=months * 30)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BOE_URL, params={"csv.x": "yes", "Datefrom": start.strftime("%d/%b/%Y"), "Dateto": end.strftime("%d/%b/%Y"), "SeriesCodes": "IUDBEDR", "CSVF": "TN", "UsingCodes": "Y"})
            resp.raise_for_status()
        rates = []
        for line in resp.text.strip().split("\\n")[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try: rates.append({"date": parts[0].strip().strip(\\'"\\'), "rate": float(parts[1].strip().strip(\\'"\\'))})
                except: pass
        return {"current_rate": rates[-1]["rate"] if rates else None, "source": "Bank of England", "history": rates[-24:]}
    except:
        return {"current_rate": 4.5, "source": "fallback estimate", "history": []}


async def fetch_exchange_rates(base: str = "GBP", targets: list = None) -> dict:
    if targets is None:
        targets = ["USD", "EUR", "JPY", "CHF", "AUD", "CAD"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{FX_URL}/latest", params={"from": base.upper(), "to": ",".join(targets)})
            resp.raise_for_status()
            data = resp.json()
        return {"base": data.get("base"), "date": data.get("date"), "rates": data.get("rates", {}), "source": "ECB"}
    except:
        return {"base": base, "rates": {"USD": 1.27, "EUR": 1.17}, "source": "fallback"}


async def fetch_inflation(months: int = 24) -> dict:
    end = datetime.now()
    start = end - timedelta(days=months * 30)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BOE_URL, params={"csv.x": "yes", "Datefrom": start.strftime("%d/%b/%Y"), "Dateto": end.strftime("%d/%b/%Y"), "SeriesCodes": "D7BT", "CSVF": "TN", "UsingCodes": "Y"})
            resp.raise_for_status()
        data = []
        for line in resp.text.strip().split("\\n")[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try: data.append({"date": parts[0].strip().strip(\\'"\\'), "cpi_pct": float(parts[1].strip().strip(\\'"\\'))})
                except: pass
        return {"current_cpi": data[-1]["cpi_pct"] if data else None, "source": "Bank of England / ONS", "history": data}
    except:
        return {"current_cpi": 3.0, "source": "fallback estimate", "history": []}


def calculate_mortgage(price: float, deposit: float, rate: float, years: int, interest_only: bool = False) -> dict:
    loan = price - deposit
    ltv = (loan / price) * 100
    mr = rate / 100 / 12
    months = years * 12
    if interest_only:
        mp = loan * mr
        total = (mp * months) + loan
    else:
        mp = loan * (mr * (1 + mr) ** months) / ((1 + mr) ** months - 1) if mr > 0 else loan / months
        total = mp * months
    return {"property_price": price, "deposit": deposit, "loan": round(loan, 2), "ltv_pct": round(ltv, 1),
            "rate_pct": rate, "term_years": years, "type": "Interest Only" if interest_only else "Repayment",
            "monthly_payment": round(mp, 2), "total_cost": round(total, 2), "total_interest": round(total - loan, 2)}
'''

# ============================================================
# ROUTES
# ============================================================

weather_routes = '''"""Weather endpoints."""
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
'''

company_routes = '''"""Company data endpoints."""
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from app.services.companies_house import search_companies, get_company_profile, get_officers, get_filing_history

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Company Data"])

class SearchRequest(BaseModel):
    query: str = Field(..., examples=["Tesco"])
    limit: int = Field(default=10, ge=1, le=50)

class CompanyRequest(BaseModel):
    company_number: str = Field(..., examples=["00445790"])

class FilingsRequest(BaseModel):
    company_number: str = Field(..., examples=["00445790"])
    limit: int = Field(default=20, ge=1, le=50)

@router.post("/company-search", summary="Search UK companies by name")
async def company_search(body: SearchRequest):
    try: return await search_companies(body.query, body.limit)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/company-profile", summary="Full company profile")
async def company_profile(body: CompanyRequest):
    try: return await get_company_profile(body.company_number)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/officers", summary="Company officers and directors")
async def company_officers(body: CompanyRequest):
    try: return await get_officers(body.company_number)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/filings", summary="Company filing history")
async def company_filings(body: FilingsRequest):
    try: return await get_filing_history(body.company_number, body.limit)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
'''

vehicle_routes = '''"""Vehicle data endpoints."""
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
'''

finance_routes = '''"""Finance data endpoints."""
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
'''

# ============================================================
# WRITE FILES
# ============================================================

files = {
    os.path.join(SERVICES_DIR, "weather.py"): weather_service,
    os.path.join(SERVICES_DIR, "companies_house.py"): company_service,
    os.path.join(SERVICES_DIR, "vehicle.py"): vehicle_service,
    os.path.join(SERVICES_DIR, "finance.py"): finance_service,
    os.path.join(ROUTES_DIR, "weather.py"): weather_routes,
    os.path.join(ROUTES_DIR, "companies.py"): company_routes,
    os.path.join(ROUTES_DIR, "vehicle.py"): vehicle_routes,
    os.path.join(ROUTES_DIR, "finance.py"): finance_routes,
}

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)
    print(f"  Created: {os.path.relpath(path, BASE)}")

# ============================================================
# UPDATE main.py — add imports and router registrations
# ============================================================

main_path = os.path.join(BASE, "app", "main.py")
with open(main_path, "r") as f:
    main_text = f.read()

# Add new imports after the last existing router import
new_imports = """
# New domain routers
from app.routes.weather import router as weather_router
from app.routes.companies import router as companies_router
from app.routes.vehicle import router as vehicle_router
from app.routes.finance import router as finance_router
"""

# Add after council_tax import
main_text = main_text.replace(
    "from app.routes.council_tax import router as council_tax_router",
    "from app.routes.council_tax import router as council_tax_router" + new_imports,
)

# Add router registrations after council_tax
new_routers = """app.include_router(weather_router)
app.include_router(companies_router)
app.include_router(vehicle_router)
app.include_router(finance_router)
"""

main_text = main_text.replace(
    "app.include_router(council_tax_router)",
    "app.include_router(council_tax_router)\n" + new_routers,
)

# Update the .well-known/x402.json endpoint to include new endpoints
old_endpoints_end = """            {'method': 'POST', 'path': '/council-tax', 'price': '0.001', 'description': 'Council tax data'},
        ],"""

new_endpoints = """            {'method': 'POST', 'path': '/council-tax', 'price': '0.001', 'description': 'Council tax data'},
            {'method': 'POST', 'path': '/current-weather', 'price': '0.001', 'description': 'Current weather conditions'},
            {'method': 'POST', 'path': '/weather-forecast', 'price': '0.001', 'description': 'Weather forecast'},
            {'method': 'POST', 'path': '/historical-weather', 'price': '0.002', 'description': 'Historical weather'},
            {'method': 'POST', 'path': '/air-quality', 'price': '0.001', 'description': 'Air quality index'},
            {'method': 'POST', 'path': '/company-search', 'price': '0.001', 'description': 'Search UK companies'},
            {'method': 'POST', 'path': '/company-profile', 'price': '0.001', 'description': 'Company profile'},
            {'method': 'POST', 'path': '/officers', 'price': '0.001', 'description': 'Company officers'},
            {'method': 'POST', 'path': '/filings', 'price': '0.001', 'description': 'Filing history'},
            {'method': 'POST', 'path': '/vehicle-info', 'price': '0.001', 'description': 'Vehicle details'},
            {'method': 'POST', 'path': '/mot-history', 'price': '0.002', 'description': 'MOT test history'},
            {'method': 'POST', 'path': '/tax-status', 'price': '0.001', 'description': 'Vehicle tax status'},
            {'method': 'POST', 'path': '/emissions', 'price': '0.001', 'description': 'Vehicle emissions'},
            {'method': 'POST', 'path': '/interest-rates', 'price': '0.001', 'description': 'BoE base rate'},
            {'method': 'POST', 'path': '/exchange-rates', 'price': '0.001', 'description': 'Exchange rates'},
            {'method': 'POST', 'path': '/inflation', 'price': '0.001', 'description': 'UK CPI inflation'},
            {'method': 'POST', 'path': '/mortgage-calculator', 'price': '0.001', 'description': 'Mortgage calculator'},
        ],"""

if old_endpoints_end in main_text:
    main_text = main_text.replace(old_endpoints_end, new_endpoints)
    print("  Updated: .well-known/x402.json endpoints")
else:
    print("  Note: Could not update .well-known/x402.json — update manually")

# Update description
main_text = main_text.replace(
    "UK Property Data API",
    "UK Data API",
    1  # Only first occurrence (the title)
)

with open(main_path, "w") as f:
    f.write(main_text)
print(f"  Updated: app/main.py")

print("\nDone! 8 new files created, main.py updated.")
print("Now run: git add -A && git commit -m 'Add weather, company, vehicle, finance endpoints (25 total)' && git push")
