"""Tests for the agronomy helper modules."""

import math

import numpy as np
import pytest

from jazira_agri.advisor import PestAdvisor
from jazira_agri.crops import CropDatabase, SeedAdvisor
from jazira_agri.geo_spatial import IndexAnalyzer
from jazira_agri.soil import FertilizerAdvisor, SalinityChecker, SoilAnalysis, SoilAnalyzer


def test_soil_analyzer_flags_issues_and_accepts_profile():
    result = SoilAnalyzer.from_profile({"ph": 7.8, "salinity_ec": 4.5, "organic_matter": 0.7, "texture": "sandy"}).evaluate()
    assert result["status"] == "needs_attention"
    assert "alkaline_soil" in result["issues"]
    assert "salinity_risk" in result["issues"]


def test_soil_analyzer_rejects_non_finite_values():
    with pytest.raises(ValueError):
        SoilAnalyzer(ph=math.nan, salinity_ec=1)


def test_seed_advisor_uses_local_crop_data():
    assert "wheat" in SeedAdvisor.list_crops()
    result = SeedAdvisor.recommend("wheat")
    assert result["recommended"][0]["crop"] == "wheat"


def test_index_analyzer_calculates_indices_and_handles_zero_denominator():
    result = IndexAnalyzer.ndvi(np.array([[10, 0]]), np.array([[20, 0]]))
    assert result[0, 0] == pytest.approx(1 / 3)
    assert result[0, 1] == -9999
    assert IndexAnalyzer.summarize(result)["valid_pixels"] == 1


def test_pest_advisor_matches_disease_symptoms():
    result = PestAdvisor().suggest("wheat", ["yellow_stripes", "yellowing"])
    assert result["matches"][0]["disease"] == "yellow_rust"


def test_existing_package_exports_remain_available():
    assert CropDatabase
    assert SoilAnalysis
    assert SalinityChecker
    assert FertilizerAdvisor
