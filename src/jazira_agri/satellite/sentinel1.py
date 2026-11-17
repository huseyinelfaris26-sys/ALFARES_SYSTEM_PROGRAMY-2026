from __future__ import annotations

from typing import Any


class Sentinel1Client:
    """Sentinel-1 SAR metadata adapter; never claims to fetch data without a provider."""

    def __init__(self, stac_url: str | None = None) -> None:
        self.stac_url = stac_url

    def search(self, *, bbox: tuple[float, float, float, float], start_date: str, end_date: str) -> dict[str, Any]:
        if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            raise ValueError("invalid bbox")
        if not self.stac_url:
            return {"status": "not_configured", "items": [], "provider": "sentinel-1-stac"}
        return {"status": "provider_adapter_required", "items": [], "provider_url": self.stac_url, "query": {"bbox": bbox, "start_date": start_date, "end_date": end_date}}
