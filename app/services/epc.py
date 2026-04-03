"""
epc.py — EPC Energy Performance Data
======================================
Fetches Energy Performance Certificate data by postcode from the
EPC Open Data Communities API. Falls back to national averages if
no API key is configured.
"""

import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

EPC_API_URL = "https://epc.opendatacommunities.org/api/v1/domestic/search"


def _score_to_band(score: float) -> str:
    """Convert a numeric EPC score to a letter band."""
    if score >= 92:
        return "A"
    elif score >= 81:
        return "B"
    elif score >= 69:
        return "C"
    elif score >= 55:
        return "D"
    elif score >= 39:
        return "E"
    elif score >= 21:
        return "F"
    else:
        return "G"


async def fetch_epc_data(postcode: str, limit: int = 20) -> dict:
    """
    Fetch EPC data for a postcode.

    If EPC_API_KEY is not set, returns estimated national average data.
    """
    settings = get_settings()
    postcode = postcode.strip().upper()

    if not settings.epc_api_key:
        logger.info(f"No EPC API key — returning national average estimates for {postcode}")
        return {
            "postcode": postcode,
            "certificates": [],
            "total_found": 0,
            "average_score": 65,
            "average_band": "D",
            "band_distribution": {
                "A": 2, "B": 10, "C": 20, "D": 35,
                "E": 20, "F": 8, "G": 5,
            },
            "note": "Estimated national averages (no EPC API key configured)",
        }

    headers = {
        "Authorization": f"Basic {settings.epc_api_key}",
        "Accept": "application/json",
    }
    params = {"postcode": postcode, "size": limit}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(EPC_API_URL, headers=headers, params=params)
        response.raise_for_status()

    data = response.json()
    rows = data.get("rows", [])

    scores = []
    band_dist: dict[str, int] = {}
    certificates = []

    for row in rows:
        score = row.get("current-energy-efficiency")
        band = row.get("current-energy-rating", "").upper()
        if score is not None:
            try:
                scores.append(int(score))
            except (ValueError, TypeError):
                pass
        if band:
            band_dist[band] = band_dist.get(band, 0) + 1

        certificates.append({
            "address": row.get("address", ""),
            "current_score": score,
            "current_band": band,
            "potential_score": row.get("potential-energy-efficiency"),
            "potential_band": row.get("potential-energy-rating", "").upper(),
            "property_type": row.get("property-type", ""),
            "inspection_date": row.get("inspection-date", ""),
        })

    avg_score = round(sum(scores) / len(scores)) if scores else 65
    avg_band = _score_to_band(avg_score)

    return {
        "postcode": postcode,
        "certificates": certificates,
        "total_found": len(certificates),
        "average_score": avg_score,
        "average_band": avg_band,
        "band_distribution": band_dist,
    }
