from __future__ import annotations

from typing import Any


def crop_profile(crop_id: str = "barley") -> dict[str, Any]:
    from ..knowledge.loader import load_syrian_crops

    crops = load_syrian_crops()
    if crop_id != "barley" or crop_id not in crops:
        raise ValueError("barley profile is unavailable in the Syrian knowledge base")
    return crops[crop_id]
