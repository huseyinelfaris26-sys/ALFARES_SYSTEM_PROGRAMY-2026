"""Conservative pest scouting workflow using existing crop symptom knowledge."""

from __future__ import annotations

from typing import Any

from ..advisor.diagnose import diagnose
from ..knowledge.loader import load_crops, load_diseases

_PEST_IDS = {"aphids", "sunn_pest"}


class PestAdvisor:
    """Rank known insect-pest candidates from reported symptoms; never prescribes pesticides."""

    @staticmethod
    def scout(crop: str, symptoms: list[str]) -> dict[str, Any]:
        crops = load_crops()
        if crop not in crops:
            raise ValueError(f"unknown crop '{crop}'. choices: {', '.join(crops)}")
        normalized = list(dict.fromkeys(symptom.strip() for symptom in symptoms if symptom.strip()))
        triage = diagnose(crop, normalized)
        diseases = load_diseases()["diseases"]
        crop_pests = [pest_id for pest_id in _PEST_IDS if pest_id in crops[crop].get("diseases", [])]
        candidates = [
            {
                "id": item["id"],
                "name_ar": diseases[item["id"]]["name_ar"],
                "score": item["score"],
                "confidence": "preliminary; confirm by field inspection",
            }
            for item in triage["candidates"]
            if item["id"] in crop_pests
        ]
        return {
            "crop": crop,
            "symptoms_reported": normalized,
            "pest_candidates": candidates,
            "next_steps": [
                "Inspect multiple plants and both leaf surfaces; record affected plants and field location.",
                "Photograph representative symptoms and check beneficial insects before any control decision.",
                "Confirm identification and local action thresholds with an agricultural extension specialist.",
            ],
            "disclaimer": "Symptom triage is not a verified pest identification. No pesticide or dose is recommended.",
        }


__all__ = ["PestAdvisor"]
