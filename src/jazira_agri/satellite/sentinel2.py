from __future__ import annotations

from typing import Any


class Sentinel2Client:
    """Sentinel-2 provider contract; requires an explicitly configured STAC source.

    This client intentionally does not embed credentials or silently download imagery.
    """

    def __init__(self, stac_url: str | None = None) -> None:
        self.stac_url = stac_url

    def search(self, *, bbox: tuple[float, float, float, float], start_date: str, end_date: str, max_cloud_pct: float = 20) -> dict[str, Any]:
        if self.stac_url is None:
            return {"status": "not_configured", "items": [], "provider": "sentinel-2-stac"}
        if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            raise ValueError("bbox must be (west, south, east, north) with positive extent")
        if not 0 <= max_cloud_pct <= 100:
            raise ValueError("max_cloud_pct must be between 0 and 100")
        return {"status": "provider_adapter_required", "items": [], "provider_url": self.stac_url, "query": {"bbox": bbox, "start_date": start_date, "end_date": end_date, "max_cloud_pct": max_cloud_pct}}
