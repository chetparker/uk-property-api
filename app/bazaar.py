"""
bazaar.py — Discovery metadata for Coinbase Agentic.Market (Bazaar)
====================================================================
Per Coinbase x402 spec, the CDP facilitator extracts `extensions.bazaar`
from accepted-payment metadata at settle time and indexes it on
agentic.market. Each entry below describes one route's input/output
schema in agent-readable terms.

Single source of truth: imported by main.py (well-known) and
middleware/payment.py (402 challenge response).
"""

# Path → bazaar metadata. Keys MUST be the actual FastAPI route paths
# (the middleware looks up by request.url.path).
BAZAAR_METADATA: dict[str, dict] = {
    # =========================================================================
    # Property data
    # =========================================================================
    "/sold-prices": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode to search, e.g. 'SW1A 1AA'."},
                "limit": {"type": "integer", "required": False, "description": "Max records to return, 1–100. Defaults to 10."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "count": {"type": "integer"},
                "results": {"type": "array", "description": "List of sold-price records: {address, price (GBP), date, property_type, new_build}."},
                "cached": {"type": "boolean"},
            },
        },
    },
    "/yield-estimate": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode, e.g. 'M1 1AA'."},
                "property_value": {"type": "number", "required": False, "description": "Property value in GBP. If omitted, the API uses the average recent sold price for the postcode."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "estimated_monthly_rent": {"type": "number", "description": "Estimated rent in GBP per month."},
                "estimated_annual_rent": {"type": "number", "description": "Estimated rent in GBP per year."},
                "property_value": {"type": "number", "description": "Property value used for the calculation in GBP."},
                "gross_yield_percent": {"type": "number"},
                "yield_band": {"type": "string", "description": "'Low' (<4%), 'Average' (4–6%), or 'High' (>6%)."},
                "cached": {"type": "boolean"},
            },
        },
    },
    "/stamp-duty": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "price": {"type": "number", "required": True, "description": "Property purchase price in GBP. Calculates UK Stamp Duty Land Tax including first-time buyer relief and additional dwelling surcharge."},
                "is_first_time_buyer": {"type": "boolean", "required": False, "description": "First-time buyers get relief on properties up to £625,000."},
                "is_additional_property": {"type": "boolean", "required": False, "description": "Second homes / buy-to-let pay a 5% surcharge (Oct 2024 rates)."},
                "is_non_resident": {"type": "boolean", "required": False, "description": "Non-UK residents pay an extra 2% surcharge."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "total_tax": {"type": "number", "description": "Total SDLT payable in GBP."},
                "effective_rate": {"type": "number", "description": "Effective tax rate as a percentage."},
                "breakdown": {"type": "array", "description": "Band-by-band breakdown: {band, rate, tax}."},
                "buyer_type": {"type": "string"},
            },
        },
    },
    "/epc-rating": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode to look up EPC certificates for."},
                "limit": {"type": "integer", "required": False, "description": "Max certificates to return, 1–100. Defaults to 20."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "certificates": {"type": "array", "description": "Per-property EPC certificates with band, score, address."},
                "total_found": {"type": "integer"},
                "average_score": {"type": "integer", "description": "Mean SAP score across certificates."},
                "average_band": {"type": "string", "description": "Mean EPC band, A–G."},
                "band_distribution": {"type": "object", "description": "Counts of certificates per band."},
            },
        },
    },
    "/crime-stats": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode. Returns recent street-level crimes from the Police UK API."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "total_crimes": {"type": "integer"},
                "by_category": {"type": "object", "description": "Crime counts grouped by category (e.g. burglary, drugs, robbery)."},
                "safety_rating": {"type": "object", "description": "{score: 1–5, label: 'Low'..'High'}."},
            },
        },
    },
    "/flood-risk": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode. Returns flood risk from rivers, sea, and surface water plus active warnings."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "overall_risk": {"type": "string", "description": "'Very Low' | 'Low' | 'Medium' | 'High'."},
                "river_and_sea_risk": {"type": "string"},
                "surface_water_risk": {"type": "string"},
                "active_warnings": {"type": "array"},
                "insurance_guidance": {"type": "string"},
            },
        },
    },
    "/planning": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode. Returns planning applications near this location."},
                "radius": {"type": "integer", "required": False, "description": "Search radius in metres, 100–5000. Defaults to 500."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "radius": {"type": "integer"},
                "applications": {"type": "array", "description": "List of planning applications with reference, description, status, date."},
            },
        },
    },
    "/council-tax": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "postcode": {"type": "string", "required": True, "description": "UK postcode. Returns council tax bands A–H for the local authority."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "local_authority": {"type": "string"},
                "band_d_rate": {"type": "number", "description": "Annual Band D rate in GBP."},
                "band_d_monthly": {"type": "number"},
                "all_bands": {"type": "object", "description": "Annual rates for bands A–H, computed from the statutory multipliers."},
                "used_national_average": {"type": "boolean"},
            },
        },
    },
    # =========================================================================
    # Weather
    # =========================================================================
    "/current-weather": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "location": {"type": "string", "required": True, "description": "City or place name, e.g. 'London'. Geocoded via Open-Meteo."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "object", "description": "{name, country, latitude, longitude}."},
                "current": {"type": "object", "description": "Live observation: temperature_c, feels_like_c, humidity_pct, precipitation_mm, wind_speed_kmh, weather_code, description, time."},
            },
        },
    },
    "/weather-forecast": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "location": {"type": "string", "required": True, "description": "City or place name."},
                "days": {"type": "integer", "required": False, "description": "Forecast horizon in days, 1–16. Defaults to 7."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "object"},
                "forecast": {"type": "array", "description": "Per-day forecast entries: temp_max_c, temp_min_c, precipitation_mm, weather_code, date."},
            },
        },
    },
    "/historical-weather": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "location": {"type": "string", "required": True, "description": "City or place name."},
                "start_date": {"type": "string", "required": True, "description": "ISO date (YYYY-MM-DD), inclusive."},
                "end_date": {"type": "string", "required": True, "description": "ISO date (YYYY-MM-DD), inclusive."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "object"},
                "history": {"type": "array", "description": "Daily historical records over the requested range."},
            },
        },
    },
    "/air-quality": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "location": {"type": "string", "required": True, "description": "City or place name."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "object"},
                "air_quality": {"type": "object", "description": "PM2.5, PM10, ozone, NO2 and overall European AQI."},
            },
        },
    },
    # =========================================================================
    # Companies House
    # =========================================================================
    "/company-search": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "query": {"type": "string", "required": True, "description": "Free-text query against UK Companies House (name, partial name, etc.)."},
                "limit": {"type": "integer", "required": False, "description": "Max matches to return, 1–50. Defaults to 10."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "total_results": {"type": "integer"},
                "results": {"type": "array", "description": "Matches: {company_number, title, company_status, date_of_creation, address}."},
            },
        },
    },
    "/company-profile": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "company_number": {"type": "string", "required": True, "description": "UK Companies House registration number, e.g. '00445790'."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
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
        },
    },
    "/officers": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "company_number": {"type": "string", "required": True, "description": "UK Companies House registration number."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "company_number": {"type": "string"},
                "total_results": {"type": "integer"},
                "officers": {"type": "array", "description": "Directors and secretaries: {name, officer_role, appointed_on, resigned_on?}."},
            },
        },
    },
    "/filings": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "company_number": {"type": "string", "required": True, "description": "UK Companies House registration number."},
                "limit": {"type": "integer", "required": False, "description": "Max filings to return, 1–50. Defaults to 20."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "company_number": {"type": "string"},
                "total_count": {"type": "integer"},
                "filings": {"type": "array", "description": "Filing history entries: {date, type, description, category}."},
            },
        },
    },
    # =========================================================================
    # DVLA / DVSA vehicle
    # =========================================================================
    "/vehicle-info": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "registration": {"type": "string", "required": True, "description": "UK vehicle registration plate (no spaces), e.g. 'AB12CDE'."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string"},
                "make": {"type": "string"},
                "model": {"type": "string"},
                "colour": {"type": "string"},
                "fuel_type": {"type": "string"},
                "year": {"type": "integer"},
                "engine_cc": {"type": "integer"},
                "co2": {"type": "integer", "description": "CO2 emissions in g/km."},
                "tax_status": {"type": "string"},
                "tax_due": {"type": "string"},
                "mot_status": {"type": "string"},
                "mot_expiry": {"type": "string"},
            },
        },
    },
    "/mot-history": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "registration": {"type": "string", "required": True, "description": "UK vehicle registration plate."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string"},
                "make": {"type": "string"},
                "model": {"type": "string"},
                "total_tests": {"type": "integer"},
                "tests": {"type": "array", "description": "Per-test records: {date, result, odometer, defects[]}."},
            },
        },
    },
    "/tax-status": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "registration": {"type": "string", "required": True, "description": "UK vehicle registration plate."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string"},
                "tax_status": {"type": "string"},
                "tax_due": {"type": "string"},
                "mot_status": {"type": "string"},
                "mot_expiry": {"type": "string"},
            },
        },
    },
    "/emissions": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "registration": {"type": "string", "required": True, "description": "UK vehicle registration plate."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string"},
                "fuel_type": {"type": "string"},
                "co2": {"type": "integer", "description": "CO2 emissions in g/km."},
                "engine_cc": {"type": "integer"},
            },
        },
    },
    # =========================================================================
    # Finance
    # =========================================================================
    "/interest-rates": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "months": {"type": "integer", "required": False, "description": "Months of history to return, 1–120. Defaults to 12."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "current_rate": {"type": "number", "description": "Latest Bank of England base rate, percent."},
                "source": {"type": "string"},
                "history": {"type": "array", "description": "Time series of {date, rate}."},
            },
        },
    },
    "/exchange-rates": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "base": {"type": "string", "required": False, "description": "ISO-4217 base currency. Defaults to 'GBP'."},
                "targets": {"type": "array", "required": False, "description": "List of ISO-4217 target currency codes. Omit for all available."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string"},
                "date": {"type": "string"},
                "rates": {"type": "object", "description": "Map of currency code → rate against base."},
                "source": {"type": "string"},
            },
        },
    },
    "/inflation": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "months": {"type": "integer", "required": False, "description": "Months of CPI history to return, 1–120. Defaults to 24."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "current_cpi": {"type": "number", "description": "Latest UK CPI inflation rate, percent year-on-year."},
                "source": {"type": "string"},
                "history": {"type": "array", "description": "Time series of {date, cpi_pct}."},
            },
        },
    },
    "/mortgage-calculator": {
        "discoverable": True,
        "inputSchema": {
            "bodyParams": {
                "property_price": {"type": "number", "required": True, "description": "Property purchase price in GBP."},
                "deposit": {"type": "number", "required": True, "description": "Deposit in GBP."},
                "interest_rate": {"type": "number", "required": False, "description": "Annual interest rate, percent. Defaults to 4.5."},
                "term_years": {"type": "integer", "required": False, "description": "Mortgage term in years, 1–40. Defaults to 25."},
                "is_interest_only": {"type": "boolean", "required": False, "description": "Interest-only vs repayment. Defaults to false (repayment)."},
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "property_price": {"type": "number"},
                "deposit": {"type": "number"},
                "loan": {"type": "number", "description": "Loan principal in GBP."},
                "monthly_payment": {"type": "number"},
                "total_repayment": {"type": "number"},
                "total_interest": {"type": "number"},
                "ltv_percent": {"type": "number"},
            },
        },
    },
}


def get_metadata(path: str) -> dict | None:
    """Return bazaar metadata for the given path, or None if not registered."""
    return BAZAAR_METADATA.get(path.rstrip("/") or "/")
