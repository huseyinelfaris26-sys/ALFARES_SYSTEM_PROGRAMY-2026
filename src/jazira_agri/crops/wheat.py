from __future__ import annotations

from typing import Any


def crop_profile(crop_id: str) -> dict[str, Any]:
    """Return the specialized Syrian crop knowledge record."""
    from ..knowledge.loader import load_syrian_crops

    crops = load_syrian_crops()
    if crop_id not in crops:
        raise ValueError(f"unknown Syrian priority crop: {crop_id}")
    return crops[crop_id]


def advisory_inputs(crop_id: str) -> list[str]:
    return list(crop_profile(crop_id).get("recommendation_inputs", []))
