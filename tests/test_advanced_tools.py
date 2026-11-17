from __future__ import annotations

import math
import unittest

from jazira_agri.advisor.pest_advisor import PestAdvisor
from jazira_agri.crops.seed_advisor import SeedAdvisor
from jazira_agri.geo_spatial.index_analyzer import SatelliteIndexAnalyzer
from jazira_agri.soil.analyzer import SoilAnalyzer


class AdvancedToolsTests(unittest.TestCase):
    def test_soil_analysis_classifies_and_flags_high_salinity(self):
        result = SoilAnalyzer.analyze(ph=8.0, ec_ds_m=4.2, organic_matter_pct=0.8, sand_pct=75, silt_pct=15, clay_pct=10)
        self.assertEqual(result["interpretation"]["texture"], "sandy")
        self.assertEqual(result["interpretation"]["salinity"], "high")
        self.assertTrue(result["flags"])

    def test_soil_analysis_rejects_incomplete_texture(self):
        with self.assertRaises(ValueError):
            SoilAnalyzer.analyze(ph=7, ec_ds_m=1, organic_matter_pct=2, sand_pct=50)

    def test_seed_advice_marks_unverified_data(self):
        result = SeedAdvisor.advise("wheat", "rainfed")
        self.assertFalse(result["verified"])
        self.assertIsNotNone(result["warning"])
        self.assertEqual(len(result["seed_rate_kg_per_dunum"]), 2)

    def test_ndvi_masks_zero_denominator_and_summarizes(self):
        result = SatelliteIndexAnalyzer.ndvi([1, 0, 2], [3, 0, 2])
        self.assertAlmostEqual(float(result[0]), 0.5)
        self.assertTrue(math.isnan(float(result[1])))
        summary = SatelliteIndexAnalyzer.summarize(result)
        self.assertEqual(summary["valid_pixels"], 2)
        self.assertAlmostEqual(summary["mean"], 0.0)

    def test_pest_triage_does_not_recommend_chemicals(self):
        result = PestAdvisor.scout("wheat", ["insect_seen", "sticky_leaves"])
        self.assertTrue(result["pest_candidates"])
        self.assertIn("pesticide", result["disclaimer"].lower())


if __name__ == "__main__":
    unittest.main()
