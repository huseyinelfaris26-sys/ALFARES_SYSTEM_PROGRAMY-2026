# -*- coding: utf-8 -*-
"""
jazira_agri.geo_spatial.sentinel_ndvi
=====================================

أداة مجانية لجلب صور الأقمار الصناعية Sentinel-2 وحساب مؤشر NDVI
من منطقة الجزيرة وشمال وشرق سوريا
المصادر: Copernicus Data Space Ecosystem + Open-Meteo
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
from datetime import datetime, timezone
from numbers import Real
from typing import Any, Optional

import numpy as np
import rasterio
import requests
from requests_cache import CachedSession
from tqdm import tqdm

CDSE_BASE_URL = "https://catalogue.dataspace.copernicus.eu/rest/api"
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_COLLECTION = "SENTINEL-2"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_CACHE = pathlib.Path(__file__).parent.parent.parent / "cache" / "sentinel"
NDVI_NODATA = -9999.0


def _log(msg: str, level: str = "INFO") -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sys.stderr.write(f"[{timestamp}] [{level}] {msg}\n")


def _aoi_bbox(aoi: dict[str, Any]) -> list[float]:
    """Return a validated [west, south, east, north] bbox from GeoJSON polygon(s)."""
    features = aoi.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("AOI GeoJSON must contain at least one Feature")

    points: list[tuple[float, float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            first, second = value[0], value[1]
            if isinstance(first, Real) and not isinstance(first, bool) and isinstance(second, Real) and not isinstance(second, bool):
                lon = float(first)
                lat = float(second)
                if not math.isfinite(lon) or not math.isfinite(lat):
                    raise ValueError("AOI coordinates must be finite longitude/latitude values")
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError("AOI coordinates must fall within valid longitude/latitude ranges")
                points.append((lon, lat))
                return
            for item in value:
                collect(item)

    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not isinstance(geometry, dict):
            continue
        collect(geometry.get("coordinates"))

    if not points:
        raise ValueError("AOI polygon contains no valid coordinate points")
    xs, ys = zip(*points)
    return [min(xs), min(ys), max(xs), max(ys)]


class SentinelNDVI:
    """جلب صور Sentinel-2 وحساب مؤشر NDVI."""

    def __init__(
        self,
        aoi_geojson: str,
        start_date: str,
        end_date: str,
        cache_dir: str | pathlib.Path = DEFAULT_CACHE,
        max_cloud_cover: int = 10,
    ) -> None:
        self.aoi_path = pathlib.Path(aoi_geojson)
        self.start_date = start_date
        self.end_date = end_date
        self.cache_dir = pathlib.Path(cache_dir)
        self.max_cloud_cover = max_cloud_cover
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = CachedSession(cache_name=str(self.cache_dir / "http_cache"), expire_after=-1)
        self.token: Optional[str] = None

    def _get_cdse_token(self) -> str:
        """الحصول على رمز الوصول لمنصة كوبرنيكوس."""
        response = requests.post(
            CDSE_TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": "cdse-public", "client_secret": ""},
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("Copernicus token response did not contain an access_token")
        return token

    def _load_aoi(self) -> dict[str, Any]:
        """تحميل ملف حدود المنطقة."""
        with self.aoi_path.open(encoding="utf-8") as source:
            return json.load(source)

    def search(self) -> Optional[dict[str, Any]]:
        """البحث عن أحدث صورة خالية من الغيوم تغطي المنطقة."""
        self.token = self._get_cdse_token()
        bbox = _aoi_bbox(self._load_aoi())
        params = {
            "bbox": ",".join(map(str, bbox)),
            "datetime": f"{self.start_date}/{self.end_date}",
            "collections": [CDSE_COLLECTION],
            "limit": 1,
            "sortby": "DateDesc",
            "filter": f"cloudCoverPercentage lt {self.max_cloud_cover}",
        }
        response = self.session.post(
            f"{CDSE_BASE_URL}/search",
            json=params,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=60,
        )
        response.raise_for_status()
        results = response.json().get("features", [])
        if not results:
            _log("لم يتم العثور على صور مناسبة", "WARNING")
            return None
        _log(f"تم العثور على الصورة: {results[0].get('id', 'unknown')}")
        return results[0]

    def _download_band(self, href: str, band_name: str) -> pathlib.Path:
        """تنزيل نطاق لوني محدد وحفظه محلياً."""
        band_path = self.cache_dir / f"{pathlib.Path(href).name}.tif"
        if band_path.exists():
            _log(f"موجود مسبقاً: {band_name}")
            return band_path
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        response = self.session.get(href, headers=headers, stream=True, timeout=120)
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        with band_path.open("wb") as destination, tqdm(
            desc=f"تنزيل {band_name}", total=total, unit="B", unit_scale=True
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    destination.write(chunk)
                    bar.update(len(chunk))
        return band_path

    def compute_ndvi(self, red_path: pathlib.Path, nir_path: pathlib.Path) -> pathlib.Path:
        """حساب NDVI على دفعات مع التحقق من تطابق النطاقين واحترام قيم NoData."""
        ndvi_path = self.cache_dir / "ndvi.tif"
        with rasterio.open(red_path) as src_red, rasterio.open(nir_path) as src_nir:
            if (
                src_red.width != src_nir.width
                or src_red.height != src_nir.height
                or src_red.transform != src_nir.transform
                or src_red.crs != src_nir.crs
            ):
                raise ValueError("red and NIR rasters must have matching dimensions, transform, and CRS")
            if src_red.count < 1 or src_nir.count < 1:
                raise ValueError("red and NIR rasters must contain at least one band")

            profile = src_red.profile.copy()
            profile.update(dtype=rasterio.float32, count=1, nodata=NDVI_NODATA)
            with rasterio.open(ndvi_path, "w", **profile) as dst:
                for _, window in src_red.block_windows(1):
                    red = src_red.read(1, window=window).astype(np.float32)
                    nir = src_nir.read(1, window=window).astype(np.float32)
                    valid = (src_red.read_masks(1, window=window) > 0) & (src_nir.read_masks(1, window=window) > 0)
                    if src_red.nodata is not None:
                        valid &= red != src_red.nodata
                    if src_nir.nodata is not None:
                        valid &= nir != src_nir.nodata
                    denominator = nir + red
                    valid &= np.isfinite(red) & np.isfinite(nir) & np.isfinite(denominator) & (denominator != 0)
                    output = np.full(red.shape, NDVI_NODATA, dtype=np.float32)
                    np.divide(nir - red, denominator, out=output, where=valid)
                    dst.write(output, 1, window=window)

        _log(f"تم حفظ NDVI في: {ndvi_path}")
        return ndvi_path

    def get_weather(self, lat: float, lon: float) -> dict[str, Any]:
        """جلب بيانات الطقس من Open-Meteo."""
        response = self.session.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "daily": [
                    "temperature_2m_mean",
                    "relative_humidity_2m_mean",
                    "precipitation_sum",
                    "evapotranspiration_sum",
                ],
                "timezone": "auto",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def run(self) -> Optional[pathlib.Path]:
        """تنفيذ سير العمل بالكامل: بحث → تنزيل → حساب NDVI."""
        product = self.search()
        if not product:
            return None
        assets = product.get("assets", {})
        red_href = assets.get("B04", {}).get("href")
        nir_href = assets.get("B08", {}).get("href")
        if not red_href or not nir_href:
            _log("روابط النطاقات غير متوفرة", "ERROR")
            return None
        return self.compute_ndvi(
            self._download_band(red_href, "الأحمر B04"),
            self._download_band(nir_href, "تحت الحمراء B08"),
        )


if __name__ == "__main__":
    ndvi_file = SentinelNDVI(
        aoi_geojson="data/area_of_interest.geojson",
        start_date="2026-01-01",
        end_date="2026-11-15",
    ).run()
    if ndvi_file:
        print(f"\n✅ تم إنشاء ملف NDVI: {ndvi_file.resolve()}")
    else:
        print("\n❌ لم يتم العثور على بيانات مناسبة")
