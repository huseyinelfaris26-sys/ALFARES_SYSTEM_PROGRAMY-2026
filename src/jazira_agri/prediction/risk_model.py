from __future__ import annotations

from typing import Any


def assess_risk(*, crop_id: str, observations: dict[str, Any]) -> dict[str, Any]:
    """Return a risk-data checklist only; no calibrated risk probability is claimed."""
    if crop_id not in {"wheat", "barley", "cotton"}:
        raise ValueError("unsupported priority crop")
    expected = ["weather", "soil", "growth_stage", "pest_scouting"]
    missing = [key for key in expected if observations.get(key) in (None, "", [])]
    return {"crop": crop_id, "status": "insufficient_data" if missing else "requires_model_validation", "risk_probability": None, "missing_inputs": missing, "note": "Risk probabilities require a locally calibrated and validated model."}
