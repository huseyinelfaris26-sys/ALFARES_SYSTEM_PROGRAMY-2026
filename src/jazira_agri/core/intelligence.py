from __future__ import annotations

import math
from typing import Any


def assess_input_readiness(*, crop_id: str, region_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Assess whether required field observations are present, without scoring yield."""
    required_by_crop = {
        "wheat": {"variety_id", "sowing_date", "soil_test", "seasonal_rain_mm", "growth_stage"},
        "barley": {"variety_id", "sowing_date", "soil_test", "seasonal_rain_mm", "growth_stage", "intended_use"},
        "cotton": {"variety_id", "sowing_date", "soil_test", "irrigation_water_and_availability", "growth_stage"},
    }
    if crop_id not in required_by_crop:
        raise ValueError(f"unsupported Syrian priority crop: {crop_id}")
    if not region_id:
        raise ValueError("region_id is required")
    missing = sorted(key for key in required_by_crop[crop_id] if inputs.get(key) in (None, "", []))
    return {
        "crop": crop_id,
        "region": region_id,
        "status": "data_collection_only" if missing else "requires_local_expert_review",
        "missing_inputs": missing,
        "confidence": 0.0,
        "note": "This is data completeness only, not a crop-yield prediction or agronomic prescription.",
    }


def safe_float(value: Any, name: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return result
