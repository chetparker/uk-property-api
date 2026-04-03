"""
flood_risk.py — Flood Risk Assessment
=======================================
Checks flood risk for a postcode using getthedata.com's free API
and active flood warnings from the Environment Agency.
"""

import httpx
import logging

logger = logging.getLogger(__name__)

FLOOD_RISK_URL = "https://www.getthedata.com/api/flood-risk"
FLOOD_WARNINGS_URL = "https://environment.data.gov.uk/flood-monitoring/id/floods"

RISK_DESCRIPTIONS = {
    "Very Low": "Minimal flood risk. This area has very little chance of flooding from rivers, the sea, or surface water.",
    "Low": "Low flood risk. There is a small chance of flooding in this area, mainly from surface water.",
    "Medium": "Moderate flood risk. This area has some risk of flooding from rivers, the sea, or surface water. Consider flood insurance.",
    "High": "High flood risk. This area has a significant chance of flooding. Flood insurance is strongly recommended.",
}

INSURANCE_NOTES = {
    "Very Low": "Standard home insurance should cover this property without flood exclusions.",
    "Low": "Most insurers will cover this property. Flood risk is unlikely to affect premiums.",
    "Medium": "Some insurers may charge higher premiums. Shop around for competitive flood cover.",
    "High": "Flood Re scheme may be available to help access affordable flood insurance. Contact your insurer about Flood Re eligibility.",
}


def get_risk_description(risk_level: str) -> str:
    """Return a human-readable description for a flood risk level."""
    return RISK_DESCRIPTIONS.get(risk_level, RISK_DESCRIPTIONS["Low"])


def get_insurance_note(risk_level: str) -> str:
    """Return insurance guidance for a flood risk level."""
    return INSURANCE_NOTES.get(risk_level, INSURANCE_NOTES["Low"])


async def fetch_flood_risk(postcode: str) -> dict:
    """Check flood risk for a postcode."""
    postcode = postcode.strip().upper()
    clean = postcode.replace(" ", "%20")

    # Fetch flood risk data
    async with httpx.AsyncClient(timeout=10.0) as client:
        risk_response = await client.get(f"{FLOOD_RISK_URL}/{clean}")
        risk_response.raise_for_status()

    risk_data = risk_response.json()

    # Parse risk levels from the API response
    flood_risk = risk_data.get("flood_risk", risk_data)
    river_and_sea = flood_risk.get("riverAndSeaRisk", flood_risk.get("river_and_sea_risk", "N/A"))
    surface_water = flood_risk.get("surfaceWaterRisk", flood_risk.get("surface_water_risk", "N/A"))

    # Determine overall risk (take the highest)
    risk_order = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3}
    river_level = risk_order.get(river_and_sea, 0)
    surface_level = risk_order.get(surface_water, 0)
    overall_idx = max(river_level, surface_level)
    overall_risk = {v: k for k, v in risk_order.items()}.get(overall_idx, "Low")

    # Fetch active flood warnings
    active_warnings = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            warnings_response = await client.get(FLOOD_WARNINGS_URL, params={"_limit": 50})
            if warnings_response.status_code == 200:
                warnings_data = warnings_response.json()
                items = warnings_data.get("items", [])
                for item in items:
                    area = item.get("floodArea", {})
                    active_warnings.append({
                        "severity": item.get("severityLevel", ""),
                        "description": item.get("description", ""),
                        "area": area.get("label", ""),
                        "time_raised": item.get("timeRaised", ""),
                    })
    except Exception as e:
        logger.warning(f"Could not fetch flood warnings: {e}")

    return {
        "postcode": postcode,
        "overall_risk": overall_risk,
        "river_and_sea_risk": river_and_sea,
        "surface_water_risk": surface_water,
        "risk_description": get_risk_description(overall_risk),
        "insurance_note": get_insurance_note(overall_risk),
        "active_warnings": active_warnings[:10],
    }
