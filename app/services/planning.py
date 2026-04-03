"""
planning.py — Planning Applications
=====================================
Fetches planning applications near a postcode using
the Planning Data API (planning.data.gov.uk).
"""

import httpx
import logging

logger = logging.getLogger(__name__)

POSTCODES_IO_URL = "https://api.postcodes.io/postcodes"
PLANNING_API_URL = "https://www.planning.data.gov.uk/api/v1/entity.json"


async def _geocode_postcode(postcode: str) -> dict:
    """Convert a postcode to lat/lng via postcodes.io."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{POSTCODES_IO_URL}/{postcode}")
        response.raise_for_status()
    data = response.json()
    result = data["result"]
    return {"lat": result["latitude"], "lng": result["longitude"]}


async def fetch_planning_applications(postcode: str, radius: int = 500) -> dict:
    """Fetch planning applications near a postcode."""
    postcode = postcode.strip().upper()

    coords = await _geocode_postcode(postcode)

    params = {
        "lat": coords["lat"],
        "lng": coords["lng"],
        "radius": radius,
        "limit": 50,
        "dataset": "planning-application",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(PLANNING_API_URL, params=params)
        response.raise_for_status()

    data = response.json()
    entities = data.get("entities", data.get("results", []))

    applications = []
    for entity in entities:
        applications.append({
            "reference": entity.get("reference", entity.get("entity", "")),
            "description": entity.get("name", entity.get("description", "Planning application")),
            "status": entity.get("status", "Unknown"),
            "date": entity.get("entry-date", entity.get("start-date", "")),
        })

    return {
        "postcode": postcode,
        "total_found": len(applications),
        "applications": applications,
        "search_radius_metres": radius,
        "latitude": coords["lat"],
        "longitude": coords["lng"],
    }
