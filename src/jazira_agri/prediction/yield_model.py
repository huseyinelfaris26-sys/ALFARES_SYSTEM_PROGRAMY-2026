from __future__ import annotations

from typing import Any


def estimate_yield(*, crop_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Explicitly untrained yield-model interface; never generates pseudo-precision."""
    if crop_id not in {"wheat", "barley", "cotton"}:
        raise ValueError("unsupported priority crop")
    required = ["region_id", "variety_id", "sowing_date", "soil_test", "weather_observations", "growth_stage"]
    missing = [key for key in required if inputs.get(key) in (None, "", [])]
    return {"crop": crop_id, "status": "not_trained", "yield_t_ha": None, "confidence": None, "missing_inputs": missing, "note": "No locally trained and independently validated model is configured; no yield estimate is emitted."}
