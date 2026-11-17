from __future__ import annotations

from typing import Any


def fertilizer_plan(*, crop_id: str, soil_test: dict[str, Any] | None, region_id: str) -> dict[str, Any]:
    """Return a safe data checklist, never an unsupported fertilizer rate."""
    if crop_id not in {"wheat", "barley", "cotton"}:
        raise ValueError("crop_id must be wheat, barley, or cotton")
    return {"crop": crop_id, "region": region_id, "status": "requires_lab_and_local_review", "soil_test_received": bool(soil_test), "rates": None, "required_evidence": ["soil laboratory results with units and sampling depth", "crop variety and target use", "locally reviewed recommendation source"], "note": "No fertilizer dose is prescribed by this unvalidated module."}
