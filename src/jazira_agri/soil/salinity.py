from __future__ import annotations

from typing import Any


def assess_salinity(ec_ds_m: float, *, source: str, measured_at: str) -> dict[str, Any]:
    """Return a traceable salinity measurement without asserting crop-specific thresholds."""
    if isinstance(ec_ds_m, bool) or not isinstance(ec_ds_m, int | float) or ec_ds_m < 0:
        raise ValueError("EC must be a non-negative number")
    if not source or not measured_at:
        raise ValueError("source and measured_at are required")
    return {"ec_ds_m": float(ec_ds_m), "source": source, "measured_at": measured_at, "status": "measurement_recorded", "crop_threshold": None, "note": "No Syrian crop-specific threshold is applied without verified local evidence."}
