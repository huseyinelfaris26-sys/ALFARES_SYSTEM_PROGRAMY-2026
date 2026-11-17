"""Interpret field soil measurements without inventing fertilizer prescriptions."""

from __future__ import annotations

import math
from typing import Any


class SoilAnalyzer:
    """Rule-based interpretation of common soil laboratory measurements.

    This is a screening aid, not a substitute for local laboratory methods or
    agronomic interpretation. Measurements and units must be provided explicitly.
    """

    @staticmethod
    def analyze(
        *,
        ph: float,
        ec_ds_m: float,
        organic_matter_pct: float,
        sand_pct: float | None = None,
        silt_pct: float | None = None,
        clay_pct: float | None = None,
    ) -> dict[str, Any]:
        values = {"ph": ph, "ec_ds_m": ec_ds_m, "organic_matter_pct": organic_matter_pct}
        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if not 0 <= ph <= 14:
            raise ValueError("ph must be within 0..14")
        if ec_ds_m < 0:
            raise ValueError("ec_ds_m must be non-negative")
        if not 0 <= organic_matter_pct <= 100:
            raise ValueError("organic_matter_pct must be within 0..100")

        texture_values = (sand_pct, silt_pct, clay_pct)
        if any(value is not None for value in texture_values):
            if any(value is None for value in texture_values):
                raise ValueError("provide sand_pct, silt_pct, and clay_pct together")
            for name, value in zip(("sand_pct", "silt_pct", "clay_pct"), texture_values):
                if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or not 0 <= value <= 100:
                    raise ValueError(f"{name} must be a finite percentage within 0..100")
            if not math.isclose(sum(texture_values), 100.0, abs_tol=1.0):
                raise ValueError("sand_pct + silt_pct + clay_pct must sum to 100 (±1)")

        if ph < 5.5:
            ph_class = "acidic"
        elif ph <= 7.5:
            ph_class = "near_neutral"
        elif ph <= 8.5:
            ph_class = "alkaline"
        else:
            ph_class = "strongly_alkaline"

        if ec_ds_m < 2:
            salinity_class = "low"
        elif ec_ds_m < 4:
            salinity_class = "moderate"
        elif ec_ds_m < 8:
            salinity_class = "high"
        else:
            salinity_class = "very_high"

        if organic_matter_pct < 1:
            organic_matter_class = "low"
        elif organic_matter_pct < 3:
            organic_matter_class = "moderate"
        else:
            organic_matter_class = "high"

        texture = None
        if sand_pct is not None:
            if sand_pct >= 70:
                texture = "sandy"
            elif clay_pct >= 40:
                texture = "clayey"
            elif silt_pct >= 50 and clay_pct < 27:
                texture = "silty"
            else:
                texture = "loamy"

        flags = []
        if ph_class in {"alkaline", "strongly_alkaline"}:
            flags.append("Review micronutrient availability and confirm pH with the laboratory.")
        if salinity_class in {"high", "very_high"}:
            flags.append("Assess drainage and crop salt tolerance; confirm the EC extraction method.")
        if organic_matter_class == "low":
            flags.append("Consider locally appropriate organic-matter management and retest.")

        return {
            "measurements": {
                "ph": float(ph),
                "ec_ds_m": float(ec_ds_m),
                "organic_matter_pct": float(organic_matter_pct),
                "texture_percentages": {"sand": sand_pct, "silt": silt_pct, "clay": clay_pct} if texture else None,
            },
            "interpretation": {
                "ph": ph_class,
                "salinity": salinity_class,
                "organic_matter": organic_matter_class,
                "texture": texture,
            },
            "flags": flags,
            "disclaimer": "Screening only; verify sampling depth, test method, and recommendations with a local soil laboratory or agronomist.",
        }


__all__ = ["SoilAnalyzer"]
