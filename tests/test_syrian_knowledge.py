from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jazira_agri.knowledge.loader import (
    load_crops,
    load_syrian_crops,
    load_syrian_diseases,
    load_syrian_regions,
)


class SyrianKnowledgeTests(unittest.TestCase):
    def test_syrian_crop_database_is_independent_and_prioritized(self):
        general = load_crops()
        syrian = load_syrian_crops()

        self.assertEqual(set(syrian), {"wheat", "barley", "cotton"})
        self.assertIn("cumin", general)
        self.assertNotIn("cumin", syrian)
        self.assertEqual(syrian["wheat"]["priority"], 1)
        self.assertEqual(syrian["barley"]["priority"], 2)
        self.assertEqual(syrian["cotton"]["priority"], 3)
        self.assertEqual(syrian["cotton"]["varieties"]["items"], [])

    def test_region_records_mark_unloaded_data_as_missing(self):
        regions = load_syrian_regions()
        self.assertEqual(set(regions), {"tal_abyad", "raqqa"})
        for region in regions.values():
            with self.subTest(region=region["region_id"]):
                self.assertFalse(region["soil"]["soilgrids_reference"]["data_values_imported"])
                self.assertIsNone(region["geometry"])
                self.assertEqual(region["local_weather"]["status"], "not_loaded")

    def test_disease_catalog_is_separate_and_has_no_unverified_treatment(self):
        catalog = load_syrian_diseases()
        self.assertIn("wheat_yellow_rust", catalog)
        self.assertIn("barley_net_blotch", catalog)
        self.assertIn("cotton_bollworm", catalog)
        self.assertIsNone(catalog["cotton_bollworm"]["control_guidance"])

    def test_all_syrian_knowledge_json_is_valid_and_draft(self):
        from jazira_agri.knowledge.loader import data_dir

        for filename in ("syrian_crops.json", "syrian_regions.json", "syrian_diseases.json"):
            with self.subTest(filename=filename):
                path = data_dir() / "knowledge" / filename
                with path.open(encoding="utf-8") as stream:
                    document = json.load(stream)
                self.assertFalse(document["_meta"]["verified"])
                self.assertEqual(document["_meta"]["status"], "draft_needs_local_validation")

    def test_loaders_respect_configured_data_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "knowledge").mkdir()
            (root / "knowledge" / "syrian_crops.json").write_text(
                '{"_meta": {}, "wheat": {"name_ar": "قمح تجريبي"}}', encoding="utf-8"
            )
            with patch.dict(os.environ, {"JAZIRA_DATA": str(root)}):
                self.assertEqual(load_syrian_crops(), {"wheat": {"name_ar": "قمح تجريبي"}})


if __name__ == "__main__":
    unittest.main()
