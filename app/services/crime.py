"""
crime.py — Street-Level Crime Statistics
==========================================
Fetches crime data from the Police UK API by postcode.
Step 1: Geocode postcode via postcodes.io
Step 2: Query street-level crimes from data.police.uk
"""

import httpx
import logging

logger = logging.getLogger(__name__)

POSTCODES_IO_URL = "https://api.postcodes.io/postcodes"
POLICE_API_URL = "https://data.police.uk/api/crimes-street/all-crime"

# Crime categories with human-readable labels
CRIME_CATEGORY_LABELS = {
    "anti-social-behaviour": "Anti-social Behaviour",
    "bicycle-theft": "Bicycle Theft",
    "burglary": "Burglary",
    "criminal-damage-arson": "Criminal Damage & Arson",
    "drugs": "Drugs",
    "other-crime": "Other Crime",
    "other-theft": "Other Theft",
    "possession-of-weapons": "Possession of Weapons",
    "public-order": "Public Order",
    "robbery": "Robbery",
    "shoplifting": "Shoplifting",
    "theft-from-the-person": "Theft from Person",
    "vehicle-crime": "Vehicle Crime",
    "violent-crime": "Violent Crime",
    "violence-and-sexual-offences": "Violence & Sexual Offences",
}


def _safety_rating(total: int) -> dict:
    """Return a 1-5 safety rating based on total crime count."""
    if total <= 50:
        return {"score": 5, "label": "Low"}
    elif total <= 150:
        return {"score": 4, "label": "Low-Medium"}
    elif total <= 300:
        return {"score": 3, "label": "Medium"}
    elif total <= 500:
        return {"score": 2, "label": "Medium-High"}
    else:
        return {"score": 1, "label": "High"}


async def _geocode_postcode(postcode: str) -> dict:
    """Convert a postcode to lat/lng via postcodes.io."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{POSTCODES_IO_URL}/{postcode}")
        response.raise_for_status()
    data = response.json()
    result = data["result"]
    return {"lat": result["latitude"], "lng": result["longitude"]}


async def fetch_crime_data(postcode: str) -> dict:
    """Fetch street-level crime stats for a postcode."""
    postcode = postcode.strip().upper()

    coords = await _geocode_postcode(postcode)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            POLICE_API_URL,
            params={"lat": coords["lat"], "lng": coords["lng"]},
        )
        response.raise_for_status()

    crimes = response.json()
    total = len(crimes)

    # Aggregate by category
    breakdown: dict[str, int] = {}
    for crime in crimes:
        cat = crime.get("category", "other-crime")
        label = CRIME_CATEGORY_LABELS.get(cat, cat.replace("-", " ").title())
        breakdown[label] = breakdown.get(label, 0) + 1

    # Sort by count descending
    breakdown = dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))

    safety = _safety_rating(total)

    return {
        "postcode": postcode,
        "total_crimes": total,
        "breakdown": breakdown,
        "safety_rating": safety,
        "latitude": coords["lat"],
        "longitude": coords["lng"],
    }
