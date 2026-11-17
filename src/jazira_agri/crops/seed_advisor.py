"""Conservative seed-rate guidance from the project's curated crop knowledge."""

from __future__ import annotations

from typing import Any

from ..knowledge.loader import load_crops


class SeedAdvisor:
    """Return existing seed varieties and rate ranges with their verification status."""

    @staticmethod
    def advise(crop: str, farming: str) -> dict[str, Any]:
        if farming not in {"rainfed", "irrigated"}:
            raise ValueError("farming must be 'rainfed' or 'irrigated'")
        crops = load_crops()
        if crop not in crops:
            raise ValueError(f"unknown crop '{crop}'. choices: {', '.join(crops)}")
        info = crops[crop]
        rate = info.get("seed_rate_kg_per_dunum", {}).get(farming)
        if not isinstance(rate, list) or len(rate) != 2 or any(not isinstance(value, int | float) for value in rate):
            raise ValueError(f"missing or invalid seed-rate data for {crop}/{farming}")
        return {
            "crop": crop,
            "crop_ar": info.get("name_ar"),
            "farming": farming,
            "seed_rate_kg_per_dunum": list(rate),
            "varieties": info.get("seeds", []),
            "verified": bool(info.get("verified", False)),
            "warning": None if info.get("verified", False) else "Unverified starting-point data; confirm seed variety, germination, and rate with local agricultural extension before sowing.",
        }


__all__ = ["SeedAdvisor"]
