from __future__ import annotations

import math
import unittest

from jazira_agri.advisor.recommend import classify_rain, recommend
from jazira_agri.knowledge.loader import load_region


class AdvisorValidationTests(unittest.TestCase):
    def test_rain_classification_rejects_negative_or_nan(self):
        region = load_region("tal_abyad")
        for value in (-1, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                classify_rain(region, value)

    def test_recommend_rejects_unknown_crop_before_loading_region(self):
        with self.assertRaisesRegex(ValueError, "unknown crop"):
            recommend("not-a-crop", "rainfed", region_name="not-a-region")

    def test_recommend_rejects_invalid_water_salinity(self):
        for value in (-0.1, math.nan, math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                recommend("wheat", "irrigated", water_ec=value)

    def test_region_loader_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            load_region("../README")


if __name__ == "__main__":
    unittest.main()
