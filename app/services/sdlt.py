"""
sdlt.py — Stamp Duty Land Tax Calculator
==========================================
This file contains ONLY the maths for calculating UK Stamp Duty (SDLT).
It has no web framework code, no database calls, no caching — just pure
calculation logic. This makes it easy to test and reuse.

WHAT IS STAMP DUTY?
    A tax you pay when you buy property in England or Northern Ireland.
    The tax is "progressive" — like income tax — meaning you pay different
    rates on different slices ("bands") of the price.

RATES (as of April 2025):
    Standard:
        £0 – £125,000         →  0%
        £125,001 – £250,000   →  2%
        £250,001 – £925,000   →  5%
        £925,001 – £1,500,000 →  10%
        Over £1,500,000       →  12%

    First-time buyer (properties up to £625,000):
        £0 – £300,000         →  0%
        £300,001 – £500,000   →  5%
        £500,001 – £625,000   →  standard rates apply above this

    Additional property surcharge:  +5%  on every band (since Oct 2024)
    Non-resident surcharge:         +2%  on every band

SOURCES:
    https://www.gov.uk/stamp-duty-land-tax/residential-property-rates
"""

from app.models.schemas import StampDutyBand


# =============================================================================
# Band definitions
# =============================================================================

# Each band is a tuple: (lower_bound, upper_bound, rate_as_decimal)
# "None" for upper bound means "no limit" (the top band).

STANDARD_BANDS = [
    (0,         125_000,    0.00),    # 0% on the first £125k
    (125_000,   250_000,    0.02),    # 2% on the next £125k
    (250_000,   925_000,    0.05),    # 5% on the next £675k
    (925_000,   1_500_000,  0.10),    # 10% on the next £575k
    (1_500_000, None,       0.12),    # 12% on anything above £1.5m
]

FIRST_TIME_BUYER_BANDS = [
    (0,         300_000,    0.00),    # 0% on the first £300k
    (300_000,   500_000,    0.05),    # 5% on £300k–£500k
    (500_000,   625_000,    0.05),    # 5% continues to £625k
    # Above £625k, first-time buyer relief doesn't apply — you fall
    # back to standard rates. The calling code handles this.
]

# These surcharges are ADDED to the base rate per band.
ADDITIONAL_PROPERTY_SURCHARGE = 0.05   # 5% extra (since Oct 2024)
NON_RESIDENT_SURCHARGE = 0.02          # 2% extra


# =============================================================================
# Core calculation function
# =============================================================================

def calculate_sdlt(
    price: float,
    is_first_time_buyer: bool = False,
    is_additional_property: bool = False,
    is_non_resident: bool = False,
) -> dict:
    """
    Calculate Stamp Duty Land Tax for a property purchase.

    Args:
        price:                  Purchase price in GBP.
        is_first_time_buyer:    True if the buyer qualifies for FTB relief.
        is_additional_property: True if this is a second home / buy-to-let.
        is_non_resident:        True if the buyer is not UK resident.

    Returns:
        A dictionary with:
            - total_tax:      Total SDLT payable (float)
            - effective_rate: Overall percentage of the price (float)
            - breakdown:      List of StampDutyBand objects
            - buyer_type:     Human-readable buyer category (str)
    """

    # --- Step 1: Pick the right band schedule ---

    # First-time buyers get relief ONLY on properties up to £625,000.
    # Above that threshold, standard rates apply to the full price.
    if is_first_time_buyer and price <= 625_000:
        bands = FIRST_TIME_BUYER_BANDS
        buyer_type = "First-time buyer"
    else:
        bands = STANDARD_BANDS
        # If they claimed FTB but price is too high, note that.
        if is_first_time_buyer and price > 625_000:
            buyer_type = "Standard (FTB relief not available above £625,000)"
        elif is_additional_property:
            buyer_type = "Additional property (+5% surcharge)"
        else:
            buyer_type = "Standard"

    if is_non_resident:
        buyer_type += " + non-resident (+2% surcharge)"

    # --- Step 2: Calculate the surcharge rate ---
    # Surcharges are added to EVERY band's rate.
    surcharge = 0.0
    if is_additional_property:
        surcharge += ADDITIONAL_PROPERTY_SURCHARGE
    if is_non_resident:
        surcharge += NON_RESIDENT_SURCHARGE

    # --- Step 3: Walk through each band and calculate tax ---
    total_tax = 0.0
    breakdown = []

    for lower, upper, base_rate in bands:
        # If the price doesn't reach this band, skip it.
        if price <= lower:
            break

        # How much of the price falls in this band?
        # If upper is None (the top band), everything above `lower` counts.
        band_ceiling = upper if upper is not None else price
        taxable_in_band = min(price, band_ceiling) - lower

        # The effective rate for this band = base rate + any surcharges.
        effective_band_rate = base_rate + surcharge

        # Tax for this band.
        band_tax = taxable_in_band * effective_band_rate
        total_tax += band_tax

        # Format the band for the response.
        # Example: "£125,001 – £250,000"
        upper_label = f"£{band_ceiling:,.0f}" if upper is not None else "∞"
        breakdown.append(StampDutyBand(
            band=f"£{lower:,.0f} – {upper_label}",
            rate=f"{effective_band_rate * 100:.1f}%",
            tax=round(band_tax, 2),
        ))

    # --- Step 4: Calculate the effective rate ---
    # This is the total tax as a percentage of the purchase price.
    effective_rate = (total_tax / price * 100) if price > 0 else 0.0

    return {
        "total_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 2),
        "breakdown": breakdown,
        "buyer_type": buyer_type,
    }
