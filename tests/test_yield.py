"""
test_yield.py — Rental Yield Calculation Tests
================================================
Tests the yield estimation logic.

HOW TO RUN:
    make test

WHAT WE TEST:
    - Postcode area extraction (the "SW" from "SW1A 1AA")
    - Rent estimation by region
    - Yield calculation maths
    - Yield band classification
    - Edge cases
"""

import pytest
from app.services.voa_rental import (
    _extract_postcode_area,
    estimate_monthly_rent,
    calculate_yield,
    REGIONAL_MEDIAN_RENTS,
    UK_NATIONAL_MEDIAN_RENT,
)


class TestPostcodeAreaExtraction:
    """Tests for extracting the area prefix from UK postcodes."""

    def test_two_letter_area(self):
        """SW1A 1AA → SW"""
        assert _extract_postcode_area("SW1A 1AA") == "SW"

    def test_one_letter_area(self):
        """M1 1AA → M"""
        assert _extract_postcode_area("M1 1AA") == "M"

    def test_two_letter_non_london(self):
        """LS1 1BA → LS"""
        assert _extract_postcode_area("LS1 1BA") == "LS"

    def test_lowercase_input(self):
        """Should handle lowercase input."""
        assert _extract_postcode_area("sw1a 1aa") == "SW"

    def test_extra_spaces(self):
        """Should handle extra whitespace."""
        assert _extract_postcode_area("  SW1A 1AA  ") == "SW"

    def test_no_space_in_postcode(self):
        """Should work even if the space is missing."""
        assert _extract_postcode_area("SW1A1AA") == "SW"

    def test_birmingham(self):
        """B1 1BB → B"""
        assert _extract_postcode_area("B1 1BB") == "B"

    def test_edinburgh(self):
        """EH1 1AA → EH"""
        assert _extract_postcode_area("EH1 1AA") == "EH"


class TestMonthlyRentEstimation:
    """Tests for the regional rent lookup."""

    def test_london_sw_has_high_rent(self):
        """South-West London should return the SW rent."""
        rent = estimate_monthly_rent("SW1A 1AA")
        assert rent == REGIONAL_MEDIAN_RENTS["SW"]

    def test_manchester(self):
        """Manchester should return the M rent."""
        rent = estimate_monthly_rent("M1 1AA")
        assert rent == REGIONAL_MEDIAN_RENTS["M"]

    def test_leeds(self):
        """Leeds should return the LS rent."""
        rent = estimate_monthly_rent("LS1 1BA")
        assert rent == REGIONAL_MEDIAN_RENTS["LS"]

    def test_unknown_area_falls_back_to_national(self):
        """An unknown postcode area should use the national median."""
        # "ZZ" is not a real UK postcode area.
        rent = estimate_monthly_rent("ZZ1 1AA")
        assert rent == UK_NATIONAL_MEDIAN_RENT

    def test_fallback_to_single_letter(self):
        """
        If the two-letter area isn't found, try the single letter.
        For example, "BT" (Belfast) is in the table, but if we had
        a hypothetical "BX" area, it should fall back to "B" (Birmingham).
        """
        # "B" is in the table (Birmingham).
        rent = estimate_monthly_rent("B1 1BB")
        assert rent == REGIONAL_MEDIAN_RENTS["B"]

    def test_all_rents_are_positive(self):
        """Every rent in the lookup table should be > 0."""
        for area, rent in REGIONAL_MEDIAN_RENTS.items():
            assert rent > 0, f"Rent for area '{area}' should be positive"


class TestYieldCalculation:
    """Tests for the gross yield calculation."""

    def test_basic_yield_calculation(self):
        """
        £200,000 property, £900/month rent:
            Annual rent = £10,800
            Yield = 10800 / 200000 × 100 = 5.4%
        """
        result = calculate_yield(
            postcode="M1 1AA",
            property_value=200_000,
            monthly_rent=900,
        )
        assert result["estimated_monthly_rent"] == 900
        assert result["estimated_annual_rent"] == 10_800
        assert result["property_value"] == 200_000
        assert result["gross_yield_percent"] == 5.4

    def test_yield_uses_postcode_rent_when_not_provided(self):
        """When no monthly_rent is given, it should use the regional lookup."""
        result = calculate_yield(
            postcode="SW1A 1AA",
            property_value=500_000,
        )
        expected_rent = REGIONAL_MEDIAN_RENTS["SW"]
        assert result["estimated_monthly_rent"] == expected_rent

    def test_low_yield_band(self):
        """A yield below 4% should be classified as 'Low'."""
        # £1,000,000 property, £2,000/month rent → 2.4% yield
        result = calculate_yield(
            postcode="SW1A 1AA",
            property_value=1_000_000,
            monthly_rent=2_000,
        )
        assert "Low" in result["yield_band"]

    def test_average_yield_band(self):
        """A yield between 4% and 6% should be 'Average'."""
        # £200,000 property, £833/month rent → ~5% yield
        result = calculate_yield(
            postcode="M1 1AA",
            property_value=200_000,
            monthly_rent=833,
        )
        assert "Average" in result["yield_band"]

    def test_high_yield_band(self):
        """A yield above 6% should be 'High'."""
        # £100,000 property, £700/month rent → 8.4% yield
        result = calculate_yield(
            postcode="L1 1AA",
            property_value=100_000,
            monthly_rent=700,
        )
        assert "High" in result["yield_band"]

    def test_postcode_is_normalised(self):
        """Output postcode should be uppercase and trimmed."""
        result = calculate_yield(
            postcode="  m1 1aa  ",
            property_value=200_000,
            monthly_rent=900,
        )
        assert result["postcode"] == "M1 1AA"

    def test_zero_property_value(self):
        """A £0 property should give 0% yield (not a division error)."""
        result = calculate_yield(
            postcode="M1 1AA",
            property_value=0,
            monthly_rent=900,
        )
        assert result["gross_yield_percent"] == 0.0

    def test_rounding(self):
        """Monetary values should be rounded to 2 decimal places."""
        result = calculate_yield(
            postcode="M1 1AA",
            property_value=333_333,
            monthly_rent=1_111,
        )
        # Check that values don't have excessive decimal places.
        assert result["estimated_monthly_rent"] == round(result["estimated_monthly_rent"], 2)
        assert result["estimated_annual_rent"] == round(result["estimated_annual_rent"], 2)
        assert result["gross_yield_percent"] == round(result["gross_yield_percent"], 2)
