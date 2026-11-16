from __future__ import annotations

import math
import unittest

from jazira_agri.intelligence.deficit_irrigation import (
    Crop,
    DailyWeather,
    DeficitIrrigationEngine,
    FieldConditions,
    GrowthStage,
    IrrigationInputError,
    SoilProperties,
)


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


if __name__ == "__main__":
    unittest.main()
