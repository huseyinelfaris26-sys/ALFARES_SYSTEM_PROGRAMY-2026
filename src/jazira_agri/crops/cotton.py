from __future__ import annotations

from typing import Any


def crop_profile(crop_id: str = "cotton") -> dict[str, Any]:
    from ..knowledge.loader import load_syrian_crops

    crops = load_syrian_crops()
    if crop_id != "cotton" or crop_id not in crops:
        raise ValueError("cotton profile is unavailable in the Syrian knowledge base")
    return crops[crop_id]
