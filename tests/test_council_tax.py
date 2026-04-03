"""
test_council_tax.py — Council Tax Calculator Tests
====================================================
Tests band multipliers, calculations, and data integrity.
"""

import pytest
from app.services.council_tax import (
    calculate_council_tax,
    BAND_MULTIPLIERS,
    BAND_D_RATES,
    NATIONAL_AVERAGE_BAND_D,
)


class TestBandMultipliers:
    """Tests for statutory band multipliers."""

    def test_band_a_is_six_ninths_of_d(self):
        """Band A should be 6/9 of Band D."""
        assert BAND_MULTIPLIERS["A"] == pytest.approx(6 / 9)

    def test_band_d_is_one(self):
        """Band D multiplier should be exactly 1.0."""
        assert BAND_MULTIPLIERS["D"] == 1.0

    def test_band_h_is_two(self):
        """Band H multiplier should be exactly 2.0."""
        assert BAND_MULTIPLIERS["H"] == 2.0

    def test_bands_increase_monotonically(self):
        """Each band should be more expensive than the previous one."""
        band_order = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for i in range(1, len(band_order)):
            assert BAND_MULTIPLIERS[band_order[i]] > BAND_MULTIPLIERS[band_order[i - 1]], (
                f"Band {band_order[i]} should be > Band {band_order[i - 1]}"
            )

    def test_all_eight_bands_exist(self):
        """All 8 bands A-H should be present."""
        expected = {"A", "B", "C", "D", "E", "F", "G", "H"}
        assert set(BAND_MULTIPLIERS.keys()) == expected


class TestCalculations:
    """Tests for council tax calculations."""

    def test_all_eight_bands_in_result(self):
        """calculate_council_tax should return all 8 bands."""
        result = calculate_council_tax(2000)
        assert len(result) == 8
        assert set(result.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H"}

    def test_band_d_equals_input(self):
        """Band D should equal the input rate."""
        result = calculate_council_tax(1800)
        assert result["D"] == 1800.0

    def test_westminster_band_a(self):
        """Westminster Band A = 934 * 6/9 = 622.67."""
        result = calculate_council_tax(BAND_D_RATES["Westminster"])
        assert result["A"] == pytest.approx(934 * 6 / 9, rel=1e-2)

    def test_westminster_band_h(self):
        """Westminster Band H = 934 * 2 = 1868."""
        result = calculate_council_tax(BAND_D_RATES["Westminster"])
        assert result["H"] == pytest.approx(1868.0)

    def test_manchester_band_d(self):
        """Manchester Band D should be 1753."""
        result = calculate_council_tax(BAND_D_RATES["Manchester"])
        assert result["D"] == 1753.0

    def test_liverpool_band_e(self):
        """Liverpool Band E = 2133 * 11/9."""
        result = calculate_council_tax(BAND_D_RATES["Liverpool"])
        assert result["E"] == pytest.approx(2133 * 11 / 9, rel=1e-2)


class TestNationalAverage:
    """Tests for national average fallback."""

    def test_national_average_is_sensible(self):
        """National average Band D should be between £1500 and £3000."""
        assert 1500 <= NATIONAL_AVERAGE_BAND_D <= 3000

    def test_national_average_all_bands(self):
        """National average should produce sensible bands."""
        result = calculate_council_tax(NATIONAL_AVERAGE_BAND_D)
        assert result["A"] < result["D"] < result["H"]
        assert result["A"] > 0


class TestDataIntegrity:
    """Tests for the hardcoded rates dictionary."""

    def test_major_cities_present(self):
        """Major cities should be in the rates dictionary."""
        for city in ["Westminster", "Manchester", "Birmingham", "Liverpool", "Bristol"]:
            assert city in BAND_D_RATES, f"{city} missing from BAND_D_RATES"

    def test_all_rates_positive(self):
        """All Band D rates should be positive."""
        for authority, rate in BAND_D_RATES.items():
            assert rate > 0, f"{authority} has non-positive rate: {rate}"
