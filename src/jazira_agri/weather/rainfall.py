from __future__ import annotations

from typing import Any


def summarize_rainfall(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize supplied rainfall records; missing data is not treated as zero rain."""
    valid = []
    for item in observations:
        amount = item.get("rain_mm")
        if amount is None:
            continue
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("rain_mm values must be non-negative numbers")
        if not item.get("date") or not item.get("source"):
            raise ValueError("each rainfall observation needs date and source")
        valid.append({"date": item["date"], "rain_mm": float(amount), "source": item["source"]})
    return {"count": len(valid), "total_mm": sum(row["rain_mm"] for row in valid) if valid else None, "observations": valid, "status": "observed" if valid else "no_data"}
