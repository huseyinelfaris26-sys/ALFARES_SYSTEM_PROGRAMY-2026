from __future__ import annotations

import unittest

from jazira_agri.core.intelligence import assess_input_readiness, safe_float
from jazira_agri.satellite.vegetation_indices import ndvi, ndwi, summarize_index
from jazira_agri.weather.rainfall import summarize_rainfall
from jazira_agri.weather.drought import drought_readiness
from jazira_agri.prediction.yield_model import estimate_yield
from jazira_agri.prediction.risk_model import assess_risk


class ArchitectureModuleTests(unittest.TestCase):
    def test_indices_and_zero_denominator(self):
        self.assertAlmostEqual(ndvi(0.8, 0.2), 0.6)
        self.assertIsNone(ndvi(0.0, 0.0))
        self.assertAlmostEqual(ndwi(0.7, 0.3), 0.4)
        self.assertEqual(summarize_index([0.2, None, 0.4])["count"], 2)

    def test_rainfall_preserves_missing_data(self):
        self.assertIsNone(summarize_rainfall([])["total_mm"])
        result = summarize_rainfall([{"date": "2026-01-01", "rain_mm": 12, "source": "station-1"}])
        self.assertEqual(result["total_mm"], 12)
        self.assertEqual(drought_readiness(seasonal_rain_mm=None)["risk"], None)

    def test_readiness_and_prediction_do_not_fake_results(self):
        ready = assess_input_readiness(crop_id="wheat", region_id="tal_abyad", inputs={})
        self.assertEqual(ready["status"], "data_collection_only")
        self.assertIsNone(estimate_yield(crop_id="wheat", inputs={})["yield_t_ha"])
        self.assertIsNone(assess_risk(crop_id="wheat", observations={})["risk_probability"])

    def test_finite_input_guard(self):
        self.assertEqual(safe_float(2, "value", minimum=0), 2)
        with self.assertRaises(ValueError):
            safe_float(float("nan"), "value")


if __name__ == "__main__":
    unittest.main()
