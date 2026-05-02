"""
bazaar.py — Discovery metadata for Coinbase Agentic.Market (Bazaar)
====================================================================
Per Coinbase x402 spec v2, the CDP facilitator extracts
`extensions.bazaar` from accepted-payment metadata at settle time and
indexes it on agentic.market.

Each entry below uses the v2 shape:

    {
      "info":   { "input": {...realistic example...}, "output": {...} },
      "schema": { JSON Schema (draft 2020-12) for input + output },
      "category": "data-analytics",
      "tags": [...]
    }

The CDP facilitator validates `info.input` against
`schema.properties.input`. If validation fails, the resource is dropped
from the index and the EXTENSION-RESPONSES header carries
`status: rejected`.

Single source of truth: imported by main.py (well-known) and
middleware/payment.py (402 challenge response).
"""

# ---------------------------------------------------------------------------
# Builder helper — keeps each route declaration compact and consistent.
# ---------------------------------------------------------------------------

_JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def _v2(
    *,
    body_example: dict,
    body_properties: dict,
    body_required: list,
    output_example: dict,
    output_properties: dict,
    tags: list,
    category: str = "data-analytics",
) -> dict:
    """Build a v2 Bazaar metadata entry from compact inputs.

    Guarantees:
      - info.input strictly satisfies schema.properties.input
      - body_example contains every key in body_required
    """
    missing = [k for k in body_required if k not in body_example]
    if missing:
        raise ValueError(
            f"body_example is missing required keys {missing}; "
            "CDP would reject this entry."
        )

    return {
        "info": {
            "input": {
                "type": "http",
                "method": "POST",
                "bodyType": "json",
                "body": body_example,
            },
            "output": {
                "type": "json",
                "example": output_example,
            },
        },
        "schema": {
            "$schema": _JSON_SCHEMA_DRAFT,
            "type": "object",
            "properties": {
                "input": {
                    "type": "object",
                    "properties": {
                        "type": {"const": "http"},
                        "method": {"enum": ["POST"]},
                        "bodyType": {"enum": ["json"]},
                        "body": {
                            "type": "object",
                            "properties": body_properties,
                            "required": body_required,
                        },
                    },
                    "required": ["type", "method", "bodyType", "body"],
                },
                "output": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "example": {
                            "type": "object",
                            "properties": output_properties,
                        },
                    },
                },
            },
            "required": ["input"],
        },
        "category": category,
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# Route → v2 metadata. Keys are FastAPI route paths.
# ---------------------------------------------------------------------------

BAZAAR_METADATA: dict = {
    # =========================================================================
    # Property data
    # =========================================================================
    "/sold-prices": _v2(
        body_example={"postcode": "SW1A 1AA", "limit": 10},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode to search, e.g. 'SW1A 1AA'."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Max records to return. Defaults to 10."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "SW1A 1AA",
            "count": 2,
            "results": [
                {"address": "10 DOWNING STREET, LONDON", "price": 2_750_000, "date": "2024-06-14", "property_type": "T", "new_build": False},
                {"address": "12 DOWNING STREET, LONDON", "price": 1_900_000, "date": "2023-11-02", "property_type": "T", "new_build": False},
            ],
            "cached": False,
        },
        output_properties={
            "postcode": {"type": "string"},
            "count": {"type": "integer"},
            "results": {"type": "array", "description": "Sold-price records: address, price (GBP), date, property_type, new_build."},
            "cached": {"type": "boolean"},
        },
        tags=["sold-prices", "land-registry", "uk-property", "property", "uk", "real-estate", "transactions"],
    ),
    "/yield-estimate": _v2(
        body_example={"postcode": "M1 1AA", "property_value": 250000},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode."},
            "property_value": {"type": "number", "description": "Property value in GBP. If omitted, the API uses the average recent sold price for the postcode."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "M1 1AA",
            "estimated_monthly_rent": 1180,
            "estimated_annual_rent": 14160,
            "property_value": 250000,
            "gross_yield_percent": 5.66,
            "yield_band": "Average",
            "cached": False,
        },
        output_properties={
            "postcode": {"type": "string"},
            "estimated_monthly_rent": {"type": "number"},
            "estimated_annual_rent": {"type": "number"},
            "property_value": {"type": "number"},
            "gross_yield_percent": {"type": "number"},
            "yield_band": {"type": "string", "description": "'Low' (<4%), 'Average' (4-6%), or 'High' (>6%)."},
            "cached": {"type": "boolean"},
        },
        tags=["rental-yield", "buy-to-let", "uk-property", "property", "uk", "real-estate", "investment"],
    ),
    "/stamp-duty": _v2(
        body_example={
            "price": 350000,
            "is_first_time_buyer": False,
            "is_additional_property": False,
            "is_non_resident": False,
        },
        body_properties={
            "price": {"type": "number", "minimum": 0, "description": "Property purchase price in GBP."},
            "is_first_time_buyer": {"type": "boolean", "description": "First-time buyers get relief on properties up to £625,000."},
            "is_additional_property": {"type": "boolean", "description": "Second homes / buy-to-let pay a 5% surcharge (Oct 2024 rates)."},
            "is_non_resident": {"type": "boolean", "description": "Non-UK residents pay an extra 2% surcharge."},
        },
        body_required=["price"],
        output_example={
            "price": 350000,
            "total_tax": 7500,
            "effective_rate": 2.14,
            "breakdown": [
                {"band": "£0 – £125,000", "rate": "0.0%", "tax": 0},
                {"band": "£125,000 – £250,000", "rate": "2.0%", "tax": 2500},
                {"band": "£250,000 – £350,000", "rate": "5.0%", "tax": 5000},
            ],
            "buyer_type": "Standard",
        },
        output_properties={
            "price": {"type": "number"},
            "total_tax": {"type": "number", "description": "Total SDLT payable in GBP."},
            "effective_rate": {"type": "number", "description": "Effective tax rate as a percentage."},
            "breakdown": {"type": "array", "description": "Band-by-band breakdown."},
            "buyer_type": {"type": "string"},
        },
        tags=["stamp-duty", "uk-property", "tax", "sdlt", "uk", "property", "calculator", "hmrc"],
    ),
    "/epc-rating": _v2(
        body_example={"postcode": "EC1A 1BB", "limit": 20},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Max certificates to return. Defaults to 20."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "EC1A 1BB",
            "certificates": [
                {"address": "1 ST MARTIN'S LE GRAND, LONDON", "current_band": "C", "current_rating": 71, "potential_band": "B", "lodgement_date": "2023-04-12"},
            ],
            "total_found": 1,
            "average_score": 71,
            "average_band": "C",
            "band_distribution": {"A": 0, "B": 0, "C": 1, "D": 0, "E": 0, "F": 0, "G": 0},
        },
        output_properties={
            "postcode": {"type": "string"},
            "certificates": {"type": "array"},
            "total_found": {"type": "integer"},
            "average_score": {"type": "integer"},
            "average_band": {"type": "string"},
            "band_distribution": {"type": "object"},
        },
        tags=["epc", "energy-rating", "uk-property", "property", "uk", "energy-efficiency", "epb"],
    ),
    "/crime-stats": _v2(
        body_example={"postcode": "E1 6AN"},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "E1 6AN",
            "total_crimes": 184,
            "by_category": {
                "anti-social-behaviour": 42,
                "burglary": 11,
                "drugs": 9,
                "robbery": 7,
                "theft-from-the-person": 35,
                "violent-crime": 48,
                "other-theft": 32,
            },
            "safety_rating": {"score": 2, "label": "Below Average"},
        },
        output_properties={
            "postcode": {"type": "string"},
            "total_crimes": {"type": "integer"},
            "by_category": {"type": "object"},
            "safety_rating": {"type": "object"},
        },
        tags=["crime", "police", "safety", "uk-property", "property", "uk", "neighborhood"],
    ),
    "/flood-risk": _v2(
        body_example={"postcode": "DT1 1HZ"},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "DT1 1HZ",
            "overall_risk": "Low",
            "river_and_sea_risk": "Very Low",
            "surface_water_risk": "Low",
            "active_warnings": [],
            "insurance_guidance": "Most insurers will offer standard cover at this risk level.",
        },
        output_properties={
            "postcode": {"type": "string"},
            "overall_risk": {"type": "string"},
            "river_and_sea_risk": {"type": "string"},
            "surface_water_risk": {"type": "string"},
            "active_warnings": {"type": "array"},
            "insurance_guidance": {"type": "string"},
        },
        tags=["flood-risk", "environment-agency", "uk-property", "property", "uk", "insurance", "climate"],
    ),
    "/planning": _v2(
        body_example={"postcode": "BS1 4DJ", "radius": 500},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode."},
            "radius": {"type": "integer", "minimum": 100, "maximum": 5000, "description": "Search radius in metres. Defaults to 500."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "BS1 4DJ",
            "radius": 500,
            "applications": [
                {"reference": "23/04567/F", "description": "Single-storey rear extension", "status": "Approved", "date": "2024-09-18"},
                {"reference": "24/01234/A", "description": "Display of illuminated fascia signage", "status": "Pending", "date": "2025-01-04"},
            ],
        },
        output_properties={
            "postcode": {"type": "string"},
            "radius": {"type": "integer"},
            "applications": {"type": "array"},
        },
        tags=["planning", "planning-permission", "uk-property", "property", "uk", "development", "council"],
    ),
    "/council-tax": _v2(
        body_example={"postcode": "M1 1AA"},
        body_properties={
            "postcode": {"type": "string", "description": "UK postcode."},
        },
        body_required=["postcode"],
        output_example={
            "postcode": "M1 1AA",
            "local_authority": "Manchester City Council",
            "band_d_rate": 1992.13,
            "band_d_monthly": 166.01,
            "all_bands": {
                "A": 1328.09,
                "B": 1549.43,
                "C": 1770.78,
                "D": 1992.13,
                "E": 2434.83,
                "F": 2877.52,
                "G": 3320.22,
                "H": 3984.26,
            },
            "used_national_average": False,
        },
        output_properties={
            "postcode": {"type": "string"},
            "local_authority": {"type": "string"},
            "band_d_rate": {"type": "number"},
            "band_d_monthly": {"type": "number"},
            "all_bands": {"type": "object"},
            "used_national_average": {"type": "boolean"},
        },
        tags=["council-tax", "uk-property", "tax", "uk", "property", "local-authority", "valuation-office"],
    ),
    # =========================================================================
    # Weather
    # =========================================================================
    "/current-weather": _v2(
        body_example={"location": "London"},
        body_properties={
            "location": {"type": "string", "description": "City or place name. Geocoded via Open-Meteo."},
        },
        body_required=["location"],
        output_example={
            "location": {"name": "London", "country": "United Kingdom", "latitude": 51.5074, "longitude": -0.1278},
            "current": {
                "temperature_c": 12.4,
                "feels_like_c": 10.8,
                "humidity_pct": 71,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 14.2,
                "weather_code": 3,
                "description": "Overcast",
                "time": "2025-04-30T15:00",
            },
        },
        output_properties={
            "location": {"type": "object"},
            "current": {"type": "object"},
        },
        tags=["weather", "current-weather", "open-meteo", "uk", "climate", "observation"],
    ),
    "/weather-forecast": _v2(
        body_example={"location": "Manchester", "days": 7},
        body_properties={
            "location": {"type": "string", "description": "City or place name."},
            "days": {"type": "integer", "minimum": 1, "maximum": 16, "description": "Forecast horizon in days. Defaults to 7."},
        },
        body_required=["location"],
        output_example={
            "location": {"name": "Manchester", "country": "United Kingdom", "latitude": 53.4808, "longitude": -2.2426},
            "forecast": [
                {"date": "2025-05-01", "temp_max_c": 15.2, "temp_min_c": 8.1, "precipitation_mm": 1.4, "weather_code": 61},
                {"date": "2025-05-02", "temp_max_c": 14.8, "temp_min_c": 7.6, "precipitation_mm": 0.2, "weather_code": 3},
            ],
        },
        output_properties={
            "location": {"type": "object"},
            "forecast": {"type": "array"},
        },
        tags=["weather", "forecast", "open-meteo", "uk", "climate", "prediction"],
    ),
    "/historical-weather": _v2(
        body_example={"location": "Edinburgh", "start_date": "2024-01-01", "end_date": "2024-01-31"},
        body_properties={
            "location": {"type": "string", "description": "City or place name."},
            "start_date": {"type": "string", "format": "date", "description": "ISO date (YYYY-MM-DD), inclusive."},
            "end_date": {"type": "string", "format": "date", "description": "ISO date (YYYY-MM-DD), inclusive."},
        },
        body_required=["location", "start_date", "end_date"],
        output_example={
            "location": {"name": "Edinburgh", "country": "United Kingdom", "latitude": 55.9533, "longitude": -3.1883},
            "history": [
                {"date": "2024-01-01", "temp_max_c": 6.2, "temp_min_c": 1.4, "precipitation_mm": 3.1},
                {"date": "2024-01-02", "temp_max_c": 5.8, "temp_min_c": 0.9, "precipitation_mm": 0.6},
            ],
        },
        output_properties={
            "location": {"type": "object"},
            "history": {"type": "array"},
        },
        tags=["weather", "historical-weather", "open-meteo", "uk", "climate", "archive"],
    ),
    "/air-quality": _v2(
        body_example={"location": "Birmingham"},
        body_properties={
            "location": {"type": "string", "description": "City or place name."},
        },
        body_required=["location"],
        output_example={
            "location": {"name": "Birmingham", "country": "United Kingdom", "latitude": 52.4862, "longitude": -1.8904},
            "air_quality": {
                "pm2_5": 8.4,
                "pm10": 13.1,
                "ozone": 64.2,
                "no2": 11.7,
                "european_aqi": 31,
                "category": "Good",
            },
        },
        output_properties={
            "location": {"type": "object"},
            "air_quality": {"type": "object"},
        },
        tags=["air-quality", "pollution", "weather", "open-meteo", "uk", "environment", "aqi"],
    ),
    # =========================================================================
    # Companies House
    # =========================================================================
    "/company-search": _v2(
        body_example={"query": "Tesco", "limit": 10},
        body_properties={
            "query": {"type": "string", "description": "Free-text query against UK Companies House."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Max matches to return. Defaults to 10."},
        },
        body_required=["query"],
        output_example={
            "query": "Tesco",
            "total_results": 2,
            "results": [
                {"company_number": "00445790", "title": "TESCO PLC", "company_status": "active", "date_of_creation": "1947-11-27", "address": "Tesco House, Shire Park, Welwyn Garden City"},
                {"company_number": "02406289", "title": "TESCO STORES LIMITED", "company_status": "active", "date_of_creation": "1989-08-04", "address": "Tesco House, Welwyn Garden City"},
            ],
        },
        output_properties={
            "query": {"type": "string"},
            "total_results": {"type": "integer"},
            "results": {"type": "array"},
        },
        tags=["companies-house", "company-search", "uk-companies", "uk", "business", "due-diligence", "kyb"],
    ),
    "/company-profile": _v2(
        body_example={"company_number": "00445790"},
        body_properties={
            "company_number": {"type": "string", "description": "UK Companies House registration number, e.g. '00445790'."},
        },
        body_required=["company_number"],
        output_example={
            "company_number": "00445790",
            "company_name": "TESCO PLC",
            "company_status": "active",
            "type": "plc",
            "date_of_creation": "1947-11-27",
            "registered_office": {
                "address_line_1": "Tesco House, Shire Park, Kestrel Way",
                "locality": "Welwyn Garden City",
                "postal_code": "AL7 1GA",
                "country": "England",
            },
            "sic_codes": ["47110"],
            "has_charges": True,
            "has_insolvency_history": False,
        },
        output_properties={
            "company_number": {"type": "string"},
            "company_name": {"type": "string"},
            "company_status": {"type": "string"},
            "type": {"type": "string"},
            "date_of_creation": {"type": "string"},
            "registered_office": {"type": "object"},
            "sic_codes": {"type": "array"},
            "has_charges": {"type": "boolean"},
            "has_insolvency_history": {"type": "boolean"},
        },
        tags=["companies-house", "company-profile", "uk-companies", "uk", "business", "due-diligence", "kyb"],
    ),
    "/officers": _v2(
        body_example={"company_number": "00445790"},
        body_properties={
            "company_number": {"type": "string", "description": "UK Companies House registration number."},
        },
        body_required=["company_number"],
        output_example={
            "company_number": "00445790",
            "total_results": 2,
            "officers": [
                {"name": "MURPHY, Kenneth Andrew", "officer_role": "director", "appointed_on": "2020-10-01"},
                {"name": "STEWART, Imran", "officer_role": "director", "appointed_on": "2021-04-22"},
            ],
        },
        output_properties={
            "company_number": {"type": "string"},
            "total_results": {"type": "integer"},
            "officers": {"type": "array"},
        },
        tags=["companies-house", "officers", "directors", "uk-companies", "uk", "business", "due-diligence"],
    ),
    "/filings": _v2(
        body_example={"company_number": "00445790", "limit": 20},
        body_properties={
            "company_number": {"type": "string", "description": "UK Companies House registration number."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Max filings to return. Defaults to 20."},
        },
        body_required=["company_number"],
        output_example={
            "company_number": "00445790",
            "total_count": 2,
            "filings": [
                {"date": "2024-09-30", "type": "AA", "description": "Full accounts made up to 24 February 2024", "category": "accounts"},
                {"date": "2024-07-01", "type": "CS01", "description": "Confirmation statement made on 1 July 2024", "category": "confirmation-statement"},
            ],
        },
        output_properties={
            "company_number": {"type": "string"},
            "total_count": {"type": "integer"},
            "filings": {"type": "array"},
        },
        tags=["companies-house", "filings", "uk-companies", "uk", "business", "due-diligence", "accounts"],
    ),
    # =========================================================================
    # DVLA / DVSA vehicle
    # =========================================================================
    "/vehicle-info": _v2(
        body_example={"registration": "AB12CDE"},
        body_properties={
            "registration": {"type": "string", "description": "UK vehicle registration plate (no spaces), e.g. 'AB12CDE'."},
        },
        body_required=["registration"],
        output_example={
            "registration": "AB12CDE",
            "make": "FORD",
            "model": "FOCUS",
            "colour": "BLUE",
            "fuel_type": "PETROL",
            "year": 2017,
            "engine_cc": 999,
            "co2": 110,
            "tax_status": "Taxed",
            "tax_due": "2025-09-01",
            "mot_status": "Valid",
            "mot_expiry": "2025-08-12",
        },
        output_properties={
            "registration": {"type": "string"},
            "make": {"type": "string"},
            "model": {"type": "string"},
            "colour": {"type": "string"},
            "fuel_type": {"type": "string"},
            "year": {"type": "integer"},
            "engine_cc": {"type": "integer"},
            "co2": {"type": "integer"},
            "tax_status": {"type": "string"},
            "tax_due": {"type": "string"},
            "mot_status": {"type": "string"},
            "mot_expiry": {"type": "string"},
        },
        tags=["dvla", "vehicle", "vehicle-lookup", "uk-vehicle", "uk", "automotive", "registration"],
    ),
    "/mot-history": _v2(
        body_example={"registration": "AB12CDE"},
        body_properties={
            "registration": {"type": "string", "description": "UK vehicle registration plate."},
        },
        body_required=["registration"],
        output_example={
            "registration": "AB12CDE",
            "make": "FORD",
            "model": "FOCUS",
            "total_tests": 2,
            "tests": [
                {"date": "2024-08-12", "result": "PASSED", "odometer": 68_421, "defects": []},
                {"date": "2023-08-09", "result": "PASSED", "odometer": 56_109, "defects": [{"text": "Nearside front tyre worn close to legal limit", "type": "ADVISORY"}]},
            ],
        },
        output_properties={
            "registration": {"type": "string"},
            "make": {"type": "string"},
            "model": {"type": "string"},
            "total_tests": {"type": "integer"},
            "tests": {"type": "array"},
        },
        tags=["dvsa", "mot", "mot-history", "vehicle", "uk-vehicle", "uk", "automotive"],
    ),
    "/tax-status": _v2(
        body_example={"registration": "AB12CDE"},
        body_properties={
            "registration": {"type": "string", "description": "UK vehicle registration plate."},
        },
        body_required=["registration"],
        output_example={
            "registration": "AB12CDE",
            "tax_status": "Taxed",
            "tax_due": "2025-09-01",
            "mot_status": "Valid",
            "mot_expiry": "2025-08-12",
        },
        output_properties={
            "registration": {"type": "string"},
            "tax_status": {"type": "string"},
            "tax_due": {"type": "string"},
            "mot_status": {"type": "string"},
            "mot_expiry": {"type": "string"},
        },
        tags=["dvla", "vehicle-tax", "ved", "vehicle", "uk-vehicle", "uk", "automotive"],
    ),
    "/emissions": _v2(
        body_example={"registration": "AB12CDE"},
        body_properties={
            "registration": {"type": "string", "description": "UK vehicle registration plate."},
        },
        body_required=["registration"],
        output_example={
            "registration": "AB12CDE",
            "fuel_type": "PETROL",
            "co2": 110,
            "engine_cc": 999,
        },
        output_properties={
            "registration": {"type": "string"},
            "fuel_type": {"type": "string"},
            "co2": {"type": "integer"},
            "engine_cc": {"type": "integer"},
        },
        tags=["dvla", "emissions", "co2", "vehicle", "uk-vehicle", "uk", "automotive", "environment"],
    ),
    # =========================================================================
    # Finance
    # =========================================================================
    "/interest-rates": _v2(
        body_example={"months": 12},
        body_properties={
            "months": {"type": "integer", "minimum": 1, "maximum": 120, "description": "Months of history to return. Defaults to 12."},
        },
        body_required=[],
        output_example={
            "current_rate": 4.5,
            "source": "Bank of England",
            "history": [
                {"date": "2024-11-07", "rate": 4.75},
                {"date": "2024-08-01", "rate": 5.00},
                {"date": "2024-02-01", "rate": 5.25},
            ],
        },
        output_properties={
            "current_rate": {"type": "number"},
            "source": {"type": "string"},
            "history": {"type": "array"},
        },
        tags=["bank-of-england", "interest-rate", "boe", "base-rate", "uk", "finance", "monetary-policy"],
    ),
    "/exchange-rates": _v2(
        body_example={"base": "GBP", "targets": ["USD", "EUR"]},
        body_properties={
            "base": {"type": "string", "description": "ISO-4217 base currency. Defaults to 'GBP'."},
            "targets": {"type": "array", "items": {"type": "string"}, "description": "ISO-4217 target currency codes. Omit for all available."},
        },
        body_required=[],
        output_example={
            "base": "GBP",
            "date": "2025-04-30",
            "rates": {"USD": 1.247, "EUR": 1.176},
            "source": "exchangerate.host",
        },
        output_properties={
            "base": {"type": "string"},
            "date": {"type": "string"},
            "rates": {"type": "object"},
            "source": {"type": "string"},
        },
        tags=["exchange-rates", "fx", "currency", "forex", "finance", "gbp", "uk"],
    ),
    "/inflation": _v2(
        body_example={"months": 24},
        body_properties={
            "months": {"type": "integer", "minimum": 1, "maximum": 120, "description": "Months of CPI history to return. Defaults to 24."},
        },
        body_required=[],
        output_example={
            "current_cpi": 2.6,
            "source": "ONS",
            "history": [
                {"date": "2025-03", "cpi_pct": 2.6},
                {"date": "2025-02", "cpi_pct": 2.8},
                {"date": "2025-01", "cpi_pct": 3.0},
            ],
        },
        output_properties={
            "current_cpi": {"type": "number"},
            "source": {"type": "string"},
            "history": {"type": "array"},
        },
        tags=["inflation", "cpi", "ons", "uk", "finance", "macroeconomics", "consumer-prices"],
    ),
    "/mortgage-calculator": _v2(
        body_example={
            "property_price": 350000,
            "deposit": 35000,
            "interest_rate": 4.5,
            "term_years": 25,
            "is_interest_only": False,
        },
        body_properties={
            "property_price": {"type": "number", "minimum": 0, "description": "Property purchase price in GBP."},
            "deposit": {"type": "number", "minimum": 0, "description": "Deposit in GBP."},
            "interest_rate": {"type": "number", "description": "Annual interest rate, percent. Defaults to 4.5."},
            "term_years": {"type": "integer", "minimum": 1, "maximum": 40, "description": "Mortgage term in years. Defaults to 25."},
            "is_interest_only": {"type": "boolean", "description": "Interest-only vs repayment. Defaults to false (repayment)."},
        },
        body_required=["property_price", "deposit"],
        output_example={
            "property_price": 350000,
            "deposit": 35000,
            "loan": 315000,
            "monthly_payment": 1751.05,
            "total_repayment": 525315.50,
            "total_interest": 210315.50,
            "ltv_percent": 90.0,
        },
        output_properties={
            "property_price": {"type": "number"},
            "deposit": {"type": "number"},
            "loan": {"type": "number"},
            "monthly_payment": {"type": "number"},
            "total_repayment": {"type": "number"},
            "total_interest": {"type": "number"},
            "ltv_percent": {"type": "number"},
        },
        tags=["mortgage", "mortgage-calculator", "uk-property", "property", "uk", "finance", "calculator"],
    ),
}


# Short human-readable descriptions, surfaced in `paymentPayload.resource.description`
# at 402-challenge time. CDP indexes this for semantic search ranking.
ENDPOINT_DESCRIPTIONS: dict = {
    "/sold-prices": "UK HM Land Registry sold property prices by postcode.",
    "/yield-estimate": "Estimated rental yield for a UK postcode.",
    "/stamp-duty": "UK Stamp Duty Land Tax (SDLT) calculator with first-time buyer relief and surcharges.",
    "/epc-rating": "UK Energy Performance Certificate (EPC) ratings by postcode.",
    "/crime-stats": "UK street-level crime statistics by postcode (Police UK).",
    "/flood-risk": "UK flood risk by postcode (Environment Agency).",
    "/planning": "UK planning applications near a postcode.",
    "/council-tax": "UK council tax bands A–H by postcode.",
    "/current-weather": "Current weather conditions by city or place name.",
    "/weather-forecast": "Multi-day weather forecast by city or place name.",
    "/historical-weather": "Historical daily weather records over a date range.",
    "/air-quality": "Air quality index (PM2.5, PM10, ozone, NO2) by city.",
    "/company-search": "Search UK Companies House by name.",
    "/company-profile": "UK Companies House profile by registration number.",
    "/officers": "UK company officers (directors, secretaries) by company number.",
    "/filings": "UK Companies House filing history by company number.",
    "/vehicle-info": "UK DVLA vehicle details by registration plate.",
    "/mot-history": "UK DVSA MOT test history by registration plate.",
    "/tax-status": "UK vehicle tax and MOT status by registration plate.",
    "/emissions": "UK vehicle CO2 emissions and engine data by registration plate.",
    "/interest-rates": "Bank of England base rate, current and historical.",
    "/exchange-rates": "Foreign exchange rates against a base currency.",
    "/inflation": "UK CPI inflation rate, current and historical (ONS).",
    "/mortgage-calculator": "UK mortgage calculator with monthly payments and total interest.",
}


def get_metadata(path: str) -> dict | None:
    """Return v2 bazaar metadata for the given path, or None if not registered."""
    return BAZAAR_METADATA.get(path.rstrip("/") or "/")


def get_description(path: str) -> str | None:
    """Return short description for resource cataloging, or None if not registered."""
    return ENDPOINT_DESCRIPTIONS.get(path.rstrip("/") or "/")
