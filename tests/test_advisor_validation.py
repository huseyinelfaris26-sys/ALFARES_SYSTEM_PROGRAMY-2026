from __future__ import annotations

import math
import unittest

from jazira_agri.advisor.diagnose import diagnose
from jazira_agri.advisor.recommend import classify_rain, recommend
from jazira_agri.intelligence.deficit_irrigation import (
    Crop,
    DailyWeather,
    DeficitIrrigationEngine,
    FieldConditions,
    GrowthStage,
    IrrigationInputError,
    SoilProperties,
)
from jazira_agri.knowledge.loader import load_region


class AdvisorValidationTests(unittest.TestCase):
    def test_rain_classification_rejects_negative_or_nan(self):
        region = load_region("tal_abyad")
        for value in (-1, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                classify_rain(region, value)

    def test_recommend_rejects_unknown_crop(self):
        with self.assertRaisesRegex(ValueError, "unknown crop"):
            recommend("not-a-crop", "rainfed", region_name="tal_abyad")

    def test_recommend_rejects_invalid_water_salinity(self):
        for value in (-0.1, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                recommend("wheat", "irrigated", water_ec=value)

    def test_region_loader_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            load_region("../README")


class IrrigationTests(unittest.TestCase):
    def test_recommendation_is_finite_and_serializable(self):
        weather = DailyWeather(
            tmin_c=18,
            tmax_c=38,
            wind_speed_ms=2.5,
            latitude_deg=35.3,
            elevation_m=220,
            day_of_year=180,
            rh_mean_pct=30,
            solar_radiation_mj_m2=28,
        )
        conditions = FieldConditions(
            Crop.COTTON,
            GrowthStage.MID_SEASON,
            0.21,
            SoilProperties(0.30, 0.17),
            2.5,
            area_ha=2,
        )
        result = DeficitIrrigationEngine().recommend(weather, conditions)
        self.assertTrue(math.isfinite(result.et0_mm))
        self.assertEqual(result.total_volume_m3, result.volume_m3_per_ha * 2)
        self.assertIn("summary", result.to_dict())

    def test_invalid_nonfinite_weather_is_rejected(self):
        with self.assertRaises(IrrigationInputError):
            DailyWeather(
                tmin_c=18,
                tmax_c=38,
                wind_speed_ms=math.nan,
                latitude_deg=35.3,
                elevation_m=220,
                day_of_year=180,
                rh_mean_pct=30,
            )

    def test_diagnose_symptoms_match_expected_candidate(self):
        out = diagnose("wheat", ["yellow_stripes"])
        self.assertEqual(out["candidates"][0]["id"], "yellow_rust")


if __name__ == "__main__":
    unittest.main()
