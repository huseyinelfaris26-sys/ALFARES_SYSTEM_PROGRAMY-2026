from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jazira_agri.advisor.farm_advice import build_farm_advice
from jazira_agri.core.farm_management import FarmRepository


class FarmAdviceTests(unittest.TestCase):
    def test_advice_is_transparent_and_never_invents_prescription(self):
        result = build_farm_advice(crop_id="wheat", region_id="tal_abyad", inputs={"growth_stage": "tillering"})
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("variety_id", result["missing_inputs"])
        self.assertIn("جرعات", result["advice"])
        self.assertTrue(result["evidence_gaps"])

    def test_rejects_unknown_crop_region_and_bad_date(self):
        with self.assertRaises(ValueError):
            build_farm_advice(crop_id="unknown", region_id="raqqa", inputs={})
        with self.assertRaises(ValueError):
            build_farm_advice(crop_id="wheat", region_id="unknown", inputs={})
        with self.assertRaises(ValueError):
            build_farm_advice(crop_id="wheat", region_id="raqqa", inputs={"sowing_date": "not-date"})


class FarmRepositoryTests(unittest.TestCase):
    def test_empty_store_does_not_create_fabricated_farm_and_report_works(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FarmRepository(temp_dir)
            self.assertEqual(store.list_farms(), [])
            farm = store.create_farm({"name": "مزرعة اختبار", "region": "raqqa", "area_ha": 4})
            field = store.create_field(farm["id"], {"name": "قطعة 1", "area_ha": 2, "crop": "barley"})
            self.assertEqual(field["farm_id"], farm["id"])
            report = store.report(farm["id"], [])
            self.assertEqual(report["field_count"], 1)
            self.assertEqual(report["field_area_ha"], 2)


if __name__ == "__main__":
    unittest.main()
