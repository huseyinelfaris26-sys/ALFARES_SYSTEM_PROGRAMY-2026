from __future__ import annotations

import unittest

from jazira_agri.prediction.scenarios import simulate_water_scenarios


class ScenarioSimulationTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            "seasonal_rain_mm": 250,
            "irrigation_mm": 80,
            "available_soil_water_mm": 40,
            "crop_water_demand_mm": 300,
        }

    def test_computes_simple_balance_and_scenario_delta(self):
        result = simulate_water_scenarios(
            crop_id="wheat",
            region_id="tal_abyad",
            baseline=self.baseline,
            scenarios=[{"name": "rainfall_reduced", "inputs": {**self.baseline, "seasonal_rain_mm": 200}}],
        )
        self.assertEqual(result["simulation_type"], "seasonal_water_balance_sensitivity")
        self.assertEqual(result["results"][0]["assumed_water_balance_mm"], 70)
        self.assertEqual(result["results"][1]["change_vs_baseline"]["balance_delta_mm"], -50)
        self.assertIsNone(result["yield_t_ha"])
        self.assertIsNone(result["confidence"])

    def test_rejects_bad_or_missing_inputs(self):
        with self.assertRaises(ValueError):
            simulate_water_scenarios(crop_id="wheat", region_id="tal_abyad", baseline={}, scenarios=[{"name": "x", "inputs": self.baseline}])
        with self.assertRaises(ValueError):
            simulate_water_scenarios(crop_id="wheat", region_id="tal_abyad", baseline=self.baseline, scenarios=[{"name": "x", "inputs": {**self.baseline, "irrigation_mm": float("nan")}}])
        with self.assertRaises(ValueError):
            simulate_water_scenarios(crop_id="unknown", region_id="tal_abyad", baseline=self.baseline, scenarios=[{"name": "x", "inputs": self.baseline}])

    def test_enforces_scenario_limit_and_unique_names(self):
        with self.assertRaises(ValueError):
            simulate_water_scenarios(crop_id="barley", region_id="raqqa", baseline=self.baseline, scenarios=[{"name": "Baseline", "inputs": self.baseline}])
        with self.assertRaises(ValueError):
            simulate_water_scenarios(crop_id="cotton", region_id="raqqa", baseline=self.baseline, scenarios=[{"name": str(i), "inputs": self.baseline} for i in range(21)])


if __name__ == "__main__":
    unittest.main()
