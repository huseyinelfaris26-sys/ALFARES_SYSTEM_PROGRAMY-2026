"""Array-based vegetation index helpers; NumPy is an optional dependency."""

from __future__ import annotations

from typing import Any

import numpy as np


class IndexAnalyzer:
    """Calculate NDVI/NDMI from equally shaped numeric band arrays."""

    @staticmethod
    def _array(values: Any) -> np.ndarray:
        array = np.asarray(values, dtype=np.float32)
        if array.size == 0:
            raise ValueError("index input must not be empty")
        return array

    @staticmethod
    def _normalized_difference(first: Any, second: Any, first_name: str, second_name: str) -> np.ndarray:
        first_array = IndexAnalyzer._array(first)
        second_array = IndexAnalyzer._array(second)
        if first_array.shape != second_array.shape:
            raise ValueError(f"{first_name} and {second_name} arrays must have the same shape")
        denominator = first_array + second_array
        result = np.divide(
            first_array - second_array,
            denominator,
            out=np.full_like(first_array, np.nan, dtype=np.float32),
            where=denominator != 0,
        )
        return np.nan_to_num(result, nan=-9999.0, posinf=-9999.0, neginf=-9999.0)

    @staticmethod
    def ndvi(red: Any, nir: Any) -> np.ndarray:
        """Compute (NIR - RED) / (NIR + RED)."""
        return -IndexAnalyzer._normalized_difference(nir, red, "nir", "red")

    @staticmethod
    def ndmi(nir: Any, swir: Any) -> np.ndarray:
        """Compute (NIR - SWIR) / (NIR + SWIR)."""
        return IndexAnalyzer._normalized_difference(nir, swir, "nir", "swir")

    @staticmethod
    def summarize(index: Any) -> dict[str, float]:
        array = IndexAnalyzer._array(index)
        valid = array[np.isfinite(array) & (array != -9999)]
        if valid.size == 0:
            return {"min": 0.0, "max": 0.0, "mean": 0.0, "valid_pixels": 0}
        return {
            "min": float(valid.min()),
            "max": float(valid.max()),
            "mean": float(valid.mean()),
            "valid_pixels": int(valid.size),
        }


__all__ = ["IndexAnalyzer"]
