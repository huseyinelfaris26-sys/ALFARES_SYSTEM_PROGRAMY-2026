from __future__ import annotations

from typing import Any


def drought_readiness(*, seasonal_rain_mm: float | None, reference_source: str | None = None) -> dict[str, Any]:
    """Report available inputs; do not apply unverified local drought thresholds."""
    if seasonal_rain_mm is not None and (isinstance(seasonal_rain_mm, bool) or not isinstance(seasonal_rain_mm, (int, float)) or seasonal_rain_mm < 0):
        raise ValueError("seasonal_rain_mm must be a non-negative number or None")
    if seasonal_rain_mm is None:
        return {"status": "insufficient_data", "risk": None, "seasonal_rain_mm": None, "source": reference_source}
    return {"status": "observation_recorded", "risk": None, "seasonal_rain_mm": float(seasonal_rain_mm), "source": reference_source, "note": "A local, crop- and stage-calibrated drought model is not yet validated."}
