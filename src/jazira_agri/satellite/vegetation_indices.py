from __future__ import annotations

import math
from typing import Any


def ndvi(nir: float, red: float) -> float | None:
    """Compute NDVI from calibrated reflectance values; return None for invalid denominator."""
    if not math.isfinite(nir) or not math.isfinite(red):
        raise ValueError("reflectance values must be finite")
    denominator = nir + red
    if denominator == 0:
        return None
    value = (nir - red) / denominator
    return max(-1.0, min(1.0, value))


def ndwi(nir: float, swir: float) -> float | None:
    """Compute a common NIR-SWIR normalized difference water index."""
    if not math.isfinite(nir) or not math.isfinite(swir):
        raise ValueError("reflectance values must be finite")
    denominator = nir + swir
    if denominator == 0:
        return None
    return max(-1.0, min(1.0, (nir - swir) / denominator))


def summarize_index(values: list[float | None]) -> dict[str, Any]:
    valid = [value for value in values if value is not None and math.isfinite(value)]
    if not valid:
        return {"count": 0, "mean": None, "min": None, "max": None}
    return {"count": len(valid), "mean": sum(valid) / len(valid), "min": min(valid), "max": max(valid)}
