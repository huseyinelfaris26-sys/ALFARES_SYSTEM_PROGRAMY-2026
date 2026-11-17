"""Numerically stable satellite vegetation/moisture index calculations."""

from __future__ import annotations

from typing import Any

import numpy as np


class SatelliteIndexAnalyzer:
    """Calculate indices from already aligned raster bands; no network access."""

    @staticmethod
    def normalized_difference(band_a: Any, band_b: Any, *, nodata: float | None = None) -> np.ndarray:
        a = np.asarray(band_a, dtype=np.float32)
        b = np.asarray(band_b, dtype=np.float32)
        if a.shape != b.shape:
            raise ValueError("input bands must have matching shapes and alignment")
        denominator = a + b
        valid = np.isfinite(a) & np.isfinite(b) & np.isfinite(denominator) & (denominator != 0)
        if nodata is not None:
            valid &= (a != nodata) & (b != nodata)
        result = np.full(a.shape, np.nan, dtype=np.float32)
        np.divide(a - b, denominator, out=result, where=valid)
        return result

    @classmethod
    def ndvi(cls, red: Any, nir: Any, *, nodata: float | None = None) -> np.ndarray:
        """NDVI = (NIR - red) / (NIR + red); bands must be co-registered."""
        return cls.normalized_difference(red, nir, nodata=nodata)

    @classmethod
    def ndmi(cls, nir: Any, swir: Any, *, nodata: float | None = None) -> np.ndarray:
        """NDMI = (NIR - SWIR) / (NIR + SWIR); bands must be co-registered."""
        return cls.normalized_difference(nir, swir, nodata=nodata)

    @staticmethod
    def summarize(index: Any) -> dict[str, float | int | None]:
        values = np.asarray(index, dtype=np.float32)
        valid = np.isfinite(values)
        count = int(valid.sum())
        return {
            "valid_pixels": count,
            "mean": float(values[valid].mean()) if count else None,
            "min": float(values[valid].min()) if count else None,
            "max": float(values[valid].max()) if count else None,
            "valid_fraction": float(count / values.size) if values.size else 0.0,
        }


__all__ = ["SatelliteIndexAnalyzer"]
