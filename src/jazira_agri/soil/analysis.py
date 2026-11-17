from __future__ import annotations

from typing import Any


def analyze_soil_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Validate and summarize a supplied soil lab sample; does not diagnose from map data."""
    required = ("sample_id", "sampled_at", "depth_cm", "source", "properties")
    missing = [key for key in required if sample.get(key) in (None, "", {})]
    if missing:
        raise ValueError(f"missing soil sample fields: {', '.join(missing)}")
    depth = sample["depth_cm"]
    if not isinstance(depth, list) or len(depth) != 2 or not all(isinstance(v, (int, float)) for v in depth) or depth[0] < 0 or depth[0] >= depth[1]:
        raise ValueError("depth_cm must be [top, bottom] with 0 <= top < bottom")
    return {"sample_id": sample["sample_id"], "sampled_at": sample["sampled_at"], "depth_cm": depth, "source": sample["source"], "properties": sample["properties"], "status": "lab_sample_recorded", "interpretation": "Values are retained as reported; agronomic interpretation requires units, methods, and local expert review."}
