import tempfile
import unittest
from pathlib import Path

from PIL import Image

from jazira_agri.advisor.diagnose import diagnose
from jazira_agri.advisor.recommend import recommend


class BasicTests(unittest.TestCase):
    def test_rainfed_good_wheat(self):
        res = recommend("wheat", "rainfed", rain_mm=300)
        low, high = res["expected_yield"][0]["kg_per_dunum"]
        self.assertEqual((low, high), (200.0, 350.0))

    def test_drought_barley(self):
        res = recommend("barley", "rainfed", rain_mm=100)
        self.assertTrue(all(y["condition"] != "rain_good" for y in res["expected_yield"]))

    def test_salinity_warning(self):
        res = recommend("cumin", "irrigated", water_ec=5.0)
        self.assertTrue(any("ملوحة" in w for w in res["warnings"]))

    def test_diagnose_symptoms(self):
        out = diagnose("wheat", ["yellow_stripes"])
        self.assertEqual(out["candidates"][0]["id"], "yellow_rust")

    def test_diagnose_photo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "leaf.png"
            Image.new("RGB", (64, 64), (230, 200, 20)).save(p)
            out = diagnose("wheat", [], photo=p)
            self.assertIn("yellowing", out["image_hints"])


if __name__ == "__main__":
    unittest.main()
