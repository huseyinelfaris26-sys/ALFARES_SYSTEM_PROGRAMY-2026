"""Rule-based symptom advisory using the local disease knowledge base."""

from __future__ import annotations

from typing import Any

from ..knowledge.loader import load_diseases


class PestAdvisor:
    """Rank diseases by weighted observed symptoms; not a confirmed diagnosis."""

    def __init__(self) -> None:
        knowledge = load_diseases()
        self.diseases = knowledge["diseases"]
        self.valid_symptoms = set(knowledge["symptoms"])

    def suggest(self, crop: str, symptoms: list[str] | None = None) -> dict[str, Any]:
        crop_key = (crop or "").strip().lower()
        if not crop_key:
            raise ValueError("crop must be specified")
        normalized = {item.strip() for item in (symptoms or []) if isinstance(item, str) and item.strip()}
        unknown = normalized - self.valid_symptoms
        if unknown:
            raise ValueError(f"unknown symptoms: {sorted(unknown)}")

        candidates = []
        for disease_id, disease in self.diseases.items():
            if crop_key not in disease.get("crops", []):
                continue
            matched = [name for name in disease.get("symptoms", {}) if name in normalized]
            score = sum(disease["symptoms"][name] for name in matched)
            if score:
                candidates.append({
                    "disease": disease_id,
                    "name_ar": disease.get("name_ar"),
                    "name_en": disease.get("name_en"),
                    "score": score,
                    "matches": matched,
                    "treatment_ar": disease.get("treatment_ar", ""),
                })
        candidates.sort(key=lambda item: (-item["score"], item["disease"]))
        return {
            "crop": crop_key,
            "symptoms": sorted(normalized),
            "matches": candidates[:3],
            "warning": "هذا فرز أولي للأعراض فقط وليس تشخيصاً مؤكداً. راجع المرشد الزراعي قبل أي معالجة.",
        }


__all__ = ["PestAdvisor"]
