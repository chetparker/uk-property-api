"""
voa_rental.py — Rental Yield Estimation Service
=================================================
Estimates rental yields using a combination of VOA (Valuation Office Agency)
council tax band data and regional rental benchmarks.

HOW RENTAL YIELD WORKS:
    Gross Yield (%) = (Annual Rent / Property Value) × 100

    Example: A £200,000 flat renting for £900/month:
        Yield = (£900 × 12) / £200,000 × 100 = 5.4%

    Investors typically look for yields above 5%. Below 4% is considered low.

DATA SOURCES:
    In a full production system, you'd integrate with the VOA's API or the
    ONS (Office for National Statistics) Private Rental Index. For this MVP,
    we use a regional lookup table with median rents per month. These figures
    are updated quarterly based on ONS data.

    VOA API: https://voatechnical.data.gov.uk/
    ONS rental data: https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/
                     privaterentalmarketstatistics

FUTURE IMPROVEMENTS:
    - Integrate live VOA council tax band lookups.
    - Use ONS Private Rental Market Statistics API for per-postcode estimates.
    - Factor in property size (1-bed, 2-bed, etc.) for better estimates.
"""

import logging
from app.models.schemas import YieldResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Regional rental benchmarks (median £/month as of Q3 2025)
# =============================================================================
# Source: ONS Private Rental Market Summary Statistics.
# The key is a postcode area prefix (the letters before the numbers).
# For example, "SW1A 1AA" → prefix "SW".

REGIONAL_MEDIAN_RENTS: dict[str, float] = {
    # --- Greater London ---
    "E":   1_850,   # East London
    "EC":  2_200,   # City of London
    "N":   1_700,   # North London
    "NW":  1_900,   # North-West London
    "SE":  1_600,   # South-East London
    "SW":  2_100,   # South-West London (Chelsea, Fulham, etc.)
    "W":   2_000,   # West London
    "WC":  2_300,   # West Central (Bloomsbury, Holborn)

    # --- Major Cities ---
    "M":   950,     # Manchester
    "B":   800,     # Birmingham
    "L":   750,     # Liverpool
    "LS":  850,     # Leeds
    "S":   700,     # Sheffield
    "BS":  1_050,   # Bristol
    "NG":  700,     # Nottingham
    "NE":  650,     # Newcastle
    "EH":  1_000,   # Edinburgh
    "G":   800,     # Glasgow
    "CF":  800,     # Cardiff
    "BT":  650,     # Belfast

    # --- South East ---
    "RG":  1_200,   # Reading
    "OX":  1_300,   # Oxford
    "GU":  1_200,   # Guildford
    "SL":  1_300,   # Slough / Windsor
    "HP":  1_100,   # Hemel / Aylesbury
    "MK":  950,     # Milton Keynes
    "CB":  1_200,   # Cambridge
    "CM":  1_000,   # Chelmsford
    "SS":  950,     # Southend
    "CT":  850,     # Canterbury
    "BN":  1_100,   # Brighton
    "PO":  800,     # Portsmouth
    "SO":  900,     # Southampton

    # --- North / Midlands ---
    "WV":  650,     # Wolverhampton
    "ST":  600,     # Stoke
    "DE":  650,     # Derby
    "LE":  700,     # Leicester
    "CV":  750,     # Coventry
    "WR":  700,     # Worcester
    "HU":  550,     # Hull
    "DN":  575,     # Doncaster
    "BD":  600,     # Bradford
    "HX":  550,     # Halifax
    "WF":  575,     # Wakefield
    "YO":  700,     # York

    # --- South West ---
    "BA":  850,     # Bath
    "EX":  800,     # Exeter
    "PL":  700,     # Plymouth
    "TR":  750,     # Truro / Cornwall
    "TA":  700,     # Taunton
    "DT":  750,     # Dorchester
    "BH":  900,     # Bournemouth
    "SP":  800,     # Salisbury

    # --- East / Anglia ---
    "NR":  750,     # Norwich
    "IP":  700,     # Ipswich
    "CO":  800,     # Colchester
    "PE":  700,     # Peterborough
    "LN":  625,     # Lincoln
}

# Fallback used when the postcode area isn't in our lookup table.
UK_NATIONAL_MEDIAN_RENT = 850.0


def _extract_postcode_area(postcode: str) -> str:
    """
    Extract the area prefix from a UK postcode.

    UK postcodes start with 1–2 letters (the "area"), followed by a digit.
    Examples:
        "SW1A 1AA" → "SW"
        "M1 1AA"   → "M"
        "LS1 1BA"  → "LS"
        "B1 1BB"   → "B"
    """
    clean = postcode.strip().upper()
    # Walk through characters until we hit a digit.
    area = ""
    for char in clean:
        if char.isalpha():
            area += char
        else:
            break
    return area


def estimate_monthly_rent(postcode: str) -> float:
    """
    Look up the estimated monthly rent for a postcode area.

    Args:
        postcode: A UK postcode, e.g. "SW1A 1AA"

    Returns:
        Estimated monthly rent in GBP.
    """
    area = _extract_postcode_area(postcode)

    # Try the full area first (e.g. "SW"), then just the first letter (e.g. "S").
    rent = REGIONAL_MEDIAN_RENTS.get(area)
    if rent is None and len(area) > 1:
        rent = REGIONAL_MEDIAN_RENTS.get(area[0])

    if rent is None:
        logger.warning(
            f"No rental data for postcode area '{area}' — using national median"
        )
        rent = UK_NATIONAL_MEDIAN_RENT

    return rent


def calculate_yield(
    postcode: str,
    property_value: float,
    monthly_rent: float | None = None,
) -> dict:
    """
    Calculate the gross rental yield for a property.

    Args:
        postcode:        UK postcode for area-based rent estimates.
        property_value:  The property's value (or purchase price) in GBP.
        monthly_rent:    Override the estimated monthly rent (optional).

    Returns:
        A dictionary matching YieldResponse fields.
    """
    if monthly_rent is None:
        monthly_rent = estimate_monthly_rent(postcode)

    annual_rent = monthly_rent * 12
    gross_yield = (annual_rent / property_value * 100) if property_value > 0 else 0.0

    # Classify the yield into a band.
    if gross_yield < 4.0:
        yield_band = "Low (<4%)"
    elif gross_yield <= 6.0:
        yield_band = "Average (4–6%)"
    else:
        yield_band = "High (>6%)"

    return {
        "postcode": postcode.strip().upper(),
        "estimated_monthly_rent": round(monthly_rent, 2),
        "estimated_annual_rent": round(annual_rent, 2),
        "property_value": round(property_value, 2),
        "gross_yield_percent": round(gross_yield, 2),
        "yield_band": yield_band,
    }
