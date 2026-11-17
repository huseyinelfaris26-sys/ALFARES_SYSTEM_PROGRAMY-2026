"""Seed selection support using the local crop knowledge base."""

from __future__ import annotations

from typing import Any

from ..knowledge.loader import load_crops


class SeedAdvisor:
    """Expose crop seed data and optionally match a supplied soil profile."""

    @staticmethod
    def list_crops() -> list[str]:
        return sorted(load_crops())

    @staticmethod
    def recommend(crop: str | None = None, *, soil_profile: dict[str, Any] | None = None) -> dict[str, Any]:
        crops = load_crops()
        if crop is not None:
            key = crop.strip().lower()
            if key not in crops:
                raise ValueError(f"unknown crop '{crop}'. choices: {', '.join(sorted(crops))}")
            selected = {key: crops[key]}
        else:
            selected = crops

        recommended_crops = soil_profile.get("recommended_crops", []) if soil_profile else []
        if not isinstance(recommended_crops, list):
            raise ValueError("soil_profile.recommended_crops must be a list")
        soil_keys = {str(item).strip().lower() for item in recommended_crops}
        results = []
        for key, info in selected.items():
            results.append({
                "crop": key,
                "name_ar": info.get("name_ar"),
                "name_en": info.get("name_en"),
                "seed_rate_kg_per_dunum": info.get("seed_rate_kg_per_dunum", {}),
                "seeds": info.get("seeds", []),
                "matches_soil_profile": bool(soil_profile) and key in soil_keys,
                "verified": bool(info.get("verified", False)),
            })
        return {"requested_crop": crop, "recommended": results, "advisory_only": True}


__all__ = ["SeedAdvisor"]
