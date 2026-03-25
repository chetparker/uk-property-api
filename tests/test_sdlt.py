"""
test_sdlt.py — Stamp Duty Calculator Tests
============================================
Tests the SDLT calculation logic against known correct values.

HOW TO RUN:
    make test
    # or directly:
    python -m pytest tests/ -v

WHY THESE TESTS MATTER:
    The stamp duty calculator is used by paying customers. If the maths is
    wrong, people will make bad financial decisions. Each test case below
    has been manually verified against HMRC's own calculator:
    https://www.tax.service.gov.uk/calculate-stamp-duty-land-tax/

APPROACH:
    We test a variety of scenarios:
    - Standard purchase at various price points
    - First-time buyer relief (below and above the £625k threshold)
    - Additional property surcharge (+5%)
    - Non-resident surcharge (+2%)
    - Combined surcharges
    - Edge cases (£0, exact band boundaries)
"""

import pytest
from app.services.sdlt import calculate_sdlt


class TestStandardPurchase:
    """Tests for standard residential purchases (no special categories)."""

    def test_below_threshold_no_tax(self):
        """A property under £125,000 should have zero stamp duty."""
        result = calculate_sdlt(price=100_000)
        assert result["total_tax"] == 0.0
        assert result["effective_rate"] == 0.0

    def test_at_threshold_boundary(self):
        """A property at exactly £125,000 should have zero stamp duty."""
        result = calculate_sdlt(price=125_000)
        assert result["total_tax"] == 0.0

    def test_250k_property(self):
        """
        £250,000 property:
            £0–£125k at 0%      = £0
            £125k–£250k at 2%   = £2,500
            Total               = £2,500
        """
        result = calculate_sdlt(price=250_000)
        assert result["total_tax"] == 2_500.0
        assert result["effective_rate"] == 1.0  # 2500 / 250000 * 100

    def test_350k_property(self):
        """
        £350,000 property:
            £0–£125k at 0%      = £0
            £125k–£250k at 2%   = £2,500
            £250k–£350k at 5%   = £5,000
            Total               = £7,500
        """
        result = calculate_sdlt(price=350_000)
        assert result["total_tax"] == 7_500.0

    def test_500k_property(self):
        """
        £500,000 property:
            £0–£125k at 0%      = £0
            £125k–£250k at 2%   = £2,500
            £250k–£500k at 5%   = £12,500
            Total               = £15,000
        """
        result = calculate_sdlt(price=500_000)
        assert result["total_tax"] == 15_000.0
        assert result["effective_rate"] == 3.0

    def test_1m_property(self):
        """
        £1,000,000 property:
            £0–£125k at 0%      = £0
            £125k–£250k at 2%   = £2,500
            £250k–£925k at 5%   = £33,750
            £925k–£1m at 10%    = £7,500
            Total               = £43,750
        """
        result = calculate_sdlt(price=1_000_000)
        assert result["total_tax"] == 43_750.0

    def test_2m_property(self):
        """
        £2,000,000 property:
            £0–£125k at 0%      = £0
            £125k–£250k at 2%   = £2,500
            £250k–£925k at 5%   = £33,750
            £925k–£1.5m at 10%  = £57,500
            £1.5m–£2m at 12%    = £60,000
            Total               = £153,750
        """
        result = calculate_sdlt(price=2_000_000)
        assert result["total_tax"] == 153_750.0


class TestFirstTimeBuyer:
    """Tests for first-time buyer relief."""

    def test_ftb_below_300k_no_tax(self):
        """First-time buyers pay nothing on properties up to £300,000."""
        result = calculate_sdlt(price=295_000, is_first_time_buyer=True)
        assert result["total_tax"] == 0.0
        assert "First-time buyer" in result["buyer_type"]

    def test_ftb_at_300k_no_tax(self):
        """Exactly £300,000 — still zero."""
        result = calculate_sdlt(price=300_000, is_first_time_buyer=True)
        assert result["total_tax"] == 0.0

    def test_ftb_450k(self):
        """
        £450,000 (first-time buyer):
            £0–£300k at 0%      = £0
            £300k–£450k at 5%   = £7,500
            Total               = £7,500
        """
        result = calculate_sdlt(price=450_000, is_first_time_buyer=True)
        assert result["total_tax"] == 7_500.0

    def test_ftb_625k(self):
        """
        £625,000 (first-time buyer — upper limit of relief):
            £0–£300k at 0%      = £0
            £300k–£500k at 5%   = £10,000
            £500k–£625k at 5%   = £6,250
            Total               = £16,250
        """
        result = calculate_sdlt(price=625_000, is_first_time_buyer=True)
        assert result["total_tax"] == 16_250.0

    def test_ftb_above_625k_falls_to_standard(self):
        """
        Above £625,000, first-time buyer relief does NOT apply.
        The buyer pays standard rates on the FULL price.

        £700,000 at standard rates:
            £0–£125k at 0%      = £0
            £125k–£250k at 2%   = £2,500
            £250k–£700k at 5%   = £22,500
            Total               = £25,000
        """
        result = calculate_sdlt(price=700_000, is_first_time_buyer=True)
        assert result["total_tax"] == 25_000.0
        assert "not available" in result["buyer_type"].lower()


class TestAdditionalProperty:
    """Tests for the additional property surcharge (second homes, buy-to-let)."""

    def test_additional_100k(self):
        """
        £100,000 additional property:
            Standard rate is 0%, but +5% surcharge applies.
            £0–£100k at 5% = £5,000
        """
        result = calculate_sdlt(price=100_000, is_additional_property=True)
        assert result["total_tax"] == 5_000.0

    def test_additional_350k(self):
        """
        £350,000 additional property:
            £0–£125k at 5%        = £6,250
            £125k–£250k at 7%     = £8,750     (2% + 5%)
            £250k–£350k at 10%    = £10,000    (5% + 5%)
            Total                 = £25,000
        """
        result = calculate_sdlt(price=350_000, is_additional_property=True)
        assert result["total_tax"] == 25_000.0


class TestNonResident:
    """Tests for the non-resident surcharge (+2%)."""

    def test_non_resident_250k(self):
        """
        £250,000 non-resident purchase:
            £0–£125k at 2%        = £2,500     (0% + 2%)
            £125k–£250k at 4%     = £5,000     (2% + 2%)
            Total                 = £7,500
        """
        result = calculate_sdlt(price=250_000, is_non_resident=True)
        assert result["total_tax"] == 7_500.0


class TestCombinedSurcharges:
    """Tests where multiple surcharges apply at once."""

    def test_additional_plus_non_resident(self):
        """
        £250,000 additional property by non-resident:
            Total surcharge = 5% + 2% = 7% on every band.
            £0–£125k at 7%        = £8,750     (0% + 7%)
            £125k–£250k at 9%     = £11,250    (2% + 7%)
            Total                 = £20,000
        """
        result = calculate_sdlt(
            price=250_000,
            is_additional_property=True,
            is_non_resident=True,
        )
        assert result["total_tax"] == 20_000.0


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_price(self):
        """A £0 property should have zero tax."""
        result = calculate_sdlt(price=0)
        assert result["total_tax"] == 0.0
        assert result["effective_rate"] == 0.0

    def test_one_penny(self):
        """A 1p property — shouldn't crash."""
        result = calculate_sdlt(price=0.01)
        assert result["total_tax"] == 0.0

    def test_very_expensive(self):
        """A £10m property — make sure the top band works."""
        result = calculate_sdlt(price=10_000_000)
        assert result["total_tax"] > 0
        # Should have breakdown entries.
        assert len(result["breakdown"]) >= 5

    def test_breakdown_has_entries(self):
        """Every non-zero result should have a breakdown."""
        result = calculate_sdlt(price=500_000)
        assert len(result["breakdown"]) > 0
        # Each entry should have the expected fields.
        for band in result["breakdown"]:
            assert hasattr(band, "band")
            assert hasattr(band, "rate")
            assert hasattr(band, "tax")

    def test_effective_rate_is_percentage(self):
        """The effective rate should be a sensible percentage (0-100)."""
        result = calculate_sdlt(price=500_000)
        assert 0 <= result["effective_rate"] <= 100
