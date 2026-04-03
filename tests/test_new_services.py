"""
test_new_services.py — Tests for New Service Functions
=======================================================
Tests helper functions and data from the new service modules.
"""

import pytest
from app.services.epc import _score_to_band
from app.services.flood_risk import (
    get_risk_description,
    get_insurance_note,
    RISK_DESCRIPTIONS,
    INSURANCE_NOTES,
)
from app.services.crime import CRIME_CATEGORY_LABELS, _safety_rating


class TestEPCScoreToBand:
    """Tests for _score_to_band conversion."""

    def test_score_92_is_a(self):
        assert _score_to_band(92) == "A"

    def test_score_100_is_a(self):
        assert _score_to_band(100) == "A"

    def test_score_91_is_b(self):
        assert _score_to_band(91) == "B"

    def test_score_81_is_b(self):
        assert _score_to_band(81) == "B"

    def test_score_80_is_c(self):
        assert _score_to_band(80) == "C"

    def test_score_69_is_c(self):
        assert _score_to_band(69) == "C"

    def test_score_68_is_d(self):
        assert _score_to_band(68) == "D"

    def test_score_55_is_d(self):
        assert _score_to_band(55) == "D"

    def test_score_54_is_e(self):
        assert _score_to_band(54) == "E"

    def test_score_39_is_e(self):
        assert _score_to_band(39) == "E"

    def test_score_38_is_f(self):
        assert _score_to_band(38) == "F"

    def test_score_21_is_f(self):
        assert _score_to_band(21) == "F"

    def test_score_20_is_g(self):
        assert _score_to_band(20) == "G"

    def test_score_1_is_g(self):
        assert _score_to_band(1) == "G"

    def test_score_0_is_g(self):
        assert _score_to_band(0) == "G"


class TestFloodRiskDescriptions:
    """Tests for flood risk descriptions and insurance notes."""

    def test_very_low_description(self):
        desc = get_risk_description("Very Low")
        assert "minimal" in desc.lower() or "very little" in desc.lower()

    def test_low_description(self):
        desc = get_risk_description("Low")
        assert "low" in desc.lower()

    def test_medium_description(self):
        desc = get_risk_description("Medium")
        assert "moderate" in desc.lower() or "some risk" in desc.lower()

    def test_high_description(self):
        desc = get_risk_description("High")
        assert "significant" in desc.lower() or "high" in desc.lower()

    def test_all_risk_levels_have_descriptions(self):
        for level in ["Very Low", "Low", "Medium", "High"]:
            assert level in RISK_DESCRIPTIONS

    def test_high_insurance_mentions_flood_re(self):
        note = get_insurance_note("High")
        assert "Flood Re" in note

    def test_very_low_insurance_is_reassuring(self):
        note = get_insurance_note("Very Low")
        assert "standard" in note.lower() or "without" in note.lower()

    def test_all_risk_levels_have_insurance_notes(self):
        for level in ["Very Low", "Low", "Medium", "High"]:
            assert level in INSURANCE_NOTES


class TestCrimeCategoryLabels:
    """Tests for crime category labels."""

    def test_main_categories_exist(self):
        expected = [
            "anti-social-behaviour",
            "burglary",
            "robbery",
            "violent-crime",
            "shoplifting",
            "vehicle-crime",
        ]
        for cat in expected:
            assert cat in CRIME_CATEGORY_LABELS, f"Missing category: {cat}"

    def test_labels_are_human_readable(self):
        for key, label in CRIME_CATEGORY_LABELS.items():
            assert label[0].isupper(), f"Label '{label}' doesn't start with uppercase"
            assert len(label) > 2, f"Label '{label}' is too short"

    def test_at_least_10_categories(self):
        assert len(CRIME_CATEGORY_LABELS) >= 10


class TestSafetyRating:
    """Tests for crime safety rating calculation."""

    def test_low_crime_is_5(self):
        assert _safety_rating(30)["score"] == 5

    def test_50_crimes_is_5(self):
        assert _safety_rating(50)["score"] == 5

    def test_51_crimes_is_4(self):
        assert _safety_rating(51)["score"] == 4

    def test_150_crimes_is_4(self):
        assert _safety_rating(150)["score"] == 4

    def test_301_crimes_is_3(self):
        result = _safety_rating(301)
        assert result["score"] == 2  # 301-500 is score 2

    def test_high_crime_is_1(self):
        assert _safety_rating(600)["score"] == 1
        assert _safety_rating(600)["label"] == "High"
