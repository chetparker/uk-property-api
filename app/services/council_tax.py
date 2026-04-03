"""
council_tax.py — Council Tax Calculator
=========================================
Returns council tax bands and estimated annual bills based on
local authority Band D rates.

Uses postcodes.io for local authority lookup and a hardcoded
dictionary of Band D rates for major UK authorities.
"""

import httpx
import logging

logger = logging.getLogger(__name__)

POSTCODES_IO_URL = "https://api.postcodes.io/postcodes"

# Statutory multipliers relative to Band D
BAND_MULTIPLIERS = {
    "A": 6 / 9,
    "B": 7 / 9,
    "C": 8 / 9,
    "D": 9 / 9,
    "E": 11 / 9,
    "F": 13 / 9,
    "G": 15 / 9,
    "H": 18 / 9,
}

NATIONAL_AVERAGE_BAND_D = 2071

# Band D rates for ~60 major local authorities (2024/25)
BAND_D_RATES = {
    "Westminster": 934,
    "City of London": 1057,
    "Wandsworth": 972,
    "Hammersmith and Fulham": 1244,
    "Tower Hamlets": 1479,
    "Camden": 1672,
    "Islington": 1601,
    "Hackney": 1597,
    "Lambeth": 1632,
    "Southwark": 1552,
    "Kensington and Chelsea": 1351,
    "Newham": 1556,
    "Greenwich": 1691,
    "Lewisham": 1726,
    "Barnet": 1848,
    "Brent": 1683,
    "Ealing": 1693,
    "Haringey": 1855,
    "Hounslow": 1715,
    "Croydon": 1951,
    "Bromley": 1742,
    "Enfield": 1831,
    "Redbridge": 1707,
    "Waltham Forest": 1801,
    "Hillingdon": 1669,
    "Richmond upon Thames": 1967,
    "Kingston upon Thames": 2030,
    "Merton": 1749,
    "Sutton": 1833,
    "Havering": 1875,
    "Barking and Dagenham": 1667,
    "Bexley": 1745,
    "Manchester": 1753,
    "Birmingham": 1843,
    "Liverpool": 2133,
    "Leeds": 1791,
    "Sheffield": 1963,
    "Bristol": 2163,
    "Newcastle upon Tyne": 2127,
    "Nottingham": 2226,
    "Leicester": 1969,
    "Coventry": 1849,
    "Bradford": 1755,
    "Cardiff": 1665,
    "Edinburgh": 1473,
    "Glasgow": 1442,
    "Brighton and Hove": 2099,
    "Southampton": 1928,
    "Portsmouth": 1933,
    "Plymouth": 2007,
    "Reading": 1884,
    "Oxford": 2124,
    "Cambridge": 2082,
    "Bath and North East Somerset": 2003,
    "York": 1936,
    "Exeter": 2063,
    "Norwich": 2098,
    "Canterbury": 2038,
    "Sunderland": 1777,
    "Wolverhampton": 1907,
}


def calculate_council_tax(band_d_rate: int) -> dict:
    """Calculate all council tax bands from a Band D rate."""
    bands = {}
    for band, multiplier in BAND_MULTIPLIERS.items():
        bands[band] = round(band_d_rate * multiplier, 2)
    return bands


async def fetch_council_tax(postcode: str) -> dict:
    """Look up council tax for a postcode."""
    postcode = postcode.strip().upper()

    # Get local authority from postcodes.io
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{POSTCODES_IO_URL}/{postcode}")
        response.raise_for_status()

    data = response.json()
    result = data["result"]
    admin_district = result.get("admin_district", "")

    # Look up Band D rate
    band_d_rate = BAND_D_RATES.get(admin_district, NATIONAL_AVERAGE_BAND_D)
    used_national_average = admin_district not in BAND_D_RATES

    all_bands = calculate_council_tax(band_d_rate)

    return {
        "postcode": postcode,
        "local_authority": admin_district,
        "band_d_rate": band_d_rate,
        "band_d_monthly": round(band_d_rate / 10, 2),
        "all_bands": all_bands,
        "used_national_average": used_national_average,
    }
