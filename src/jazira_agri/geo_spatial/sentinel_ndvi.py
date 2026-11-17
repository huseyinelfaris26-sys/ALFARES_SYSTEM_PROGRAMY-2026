# -*- coding: utf-8 -*-
"""
jazira_agri.geo_spatial.sentinel_ndvi
=====================================

أداة مجانية لجلب صور الأقمار الصناعية Sentinel-2 وحساب مؤشر NDVI
من منطقة الجزيرة وشمال وشرق سوريا
المصادر: Copernicus Data Space Ecosystem + Microsoft Planetary Computer + Open-Meteo
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import rasterio
from rasterio.enums import Resampling
import requests
from requests_oauthlib import OAuth2Session
from requests_cache import CachedSession
from tqdm import tqdm

# ----------------------------------------------------------------------
# إعداد السجلات
# ----------------------------------------------------------------------
def _log(msg: str, level: str = "INFO") -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sys.stderr.write(f"[{timestamp}] [{level}] {msg}\n")

# ----------------------------------------------------------------------
# عناوين واجهات برمجة التطبيقات المجانية لعام 2026
# ----------------------------------------------------------------------
CDSE_BASE_URL = "https://catalogue.dataspace.copernicus.eu/rest/api"
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_COLLECTION = "SENTINEL-2"
MPC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# مجلد التخزين المؤقت الافتراضي
DEFAULT_CACHE = pathlib.Path(__file__).parent.parent.parent / "cache" / "sentinel"

# ----------------------------------------------------------------------
# الفئة الرئيسية
# ----------------------------------------------------------------------
class SentinelNDVI:
    """
    جلب صور Sentinel-2 وحساب مؤشر NDVI

    مثال الاستخدام:
        ndvi = SentinelNDVI(
            aoi_geojson="data/area_of_interest.geojson",
            start_date="2024-04-01",
            end_date="2024-04-30"
        )
        ndvi_path = ndvi.run()
    """

    def __init__(
        self,
        aoi_geojson: str,
        start_date: str,
        end_date: str,
        cache_dir: str | pathlib.Path = DEFAULT_CACHE,
        max_cloud_cover: int = 10
    ):
        self.aoi_path = pathlib.Path(aoi_geojson)
        self.start_date = start_date
        self.end_date = end_date
        self.cache_dir = pathlib.Path(cache_dir)
        self.max_cloud_cover = max_cloud_cover
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = CachedSession(
            cache_name=str(self.cache_dir / "http_cache"),
            expire_after=-1
        )
        self.token: Optional[str] = None

    def _get_cdse_token(self) -> str:
        """الحصول على رمز الوصول لمنصة كوبرنيكوس"""
        data = {
            "grant_type": "client_credentials",
            "client_id": "cdse-public",
            "client_secret": "",
        }
        resp = requests.post(CDSE_TOKEN_URL, data=data, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _load_aoi(self) -> dict:
        """تحميل ملف حدود المنطقة"""
        with open(self.aoi_path, encoding="utf-8") as f:
            return json.load(f)

    def search(self) -> Optional[dict]:
        """البحث عن أحدث صورة خالية من الغيوم تغطي المنطقة"""
        self.token = self._get_cdse_token()
        aoi = self._load_aoi()
        coords = aoi["features"][0]["geometry"]["coordinates"][0][0]
        bbox = [min(c[0] for c in coords), min(c[1] for c in coords),
                max(c[0] for c in coords), max(c[1] for c in coords)]

        params = {
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "datetime": f"{self.start_date}/{self.end_date}",
            "collections": [CDSE_COLLECTION],
            "limit": 1,
            "sortby": "DateDesc",
            "filter": f"cloudCoverPercentage lt {self.max_cloud_cover}"
        }

        headers = {"Authorization": f"Bearer {self.token}"}
        resp = self.session.post(
            f"{CDSE_BASE_URL}/search",
            json=params,
            headers=headers,
            timeout=60
        )
        resp.raise_for_status()
        results = resp.json()["features"]
        if not results:
            _log("لم يتم العثور على صور مناسبة", "WARNING")
            return None
        _log(f"تم العثور على الصورة: {results[0]['id']}")
        return results[0]

    def _download_band(self, href: str, band_name: str) -> pathlib.Path:
        """تنزيل نطاق لوني محدد وحفظه محلياً"""
        band_path = self.cache_dir / f"{pathlib.Path(href).name}.tif"
        if band_path.exists():
            _log(f"موجود مسبقاً: {band_name}")
            return band_path

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp = self.session.get(href, headers=headers, stream=True, timeout=120)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        with open(band_path, "wb") as f, tqdm(
            desc=f"تنزيل {band_name}",
            total=total,
            unit="B",
            unit_scale=True
        ) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        return band_path

    def compute_ndvi(self, red_path: pathlib.Path, nir_path: pathlib.Path) -> pathlib.Path:
        """حساب مؤشر NDVI من النطاق الأحمر ونطاق الأشعة تحت الحمراء القريبة"""
        ndvi_path = self.cache_dir / "ndvi.tif"

        with rasterio.open(red_path) as src_red, rasterio.open(nir_path) as src_nir:
            kwargs = src_red.profile.copy()
            kwargs.update(dtype=rasterio.float32, count=1, nodata=-9999)

            with rasterio.open(ndvi_path, "w", **kwargs) as dst:
                for _, window in src_red.block_windows(1):
                    red_block = src_red.read(1, window=window).astype(np.float32)
                    nir_block = src_nir.read(1, window=window).astype(np.float32)
                    denom = nir_block + red_block
                    ndvi_block = np.divide(
                        nir_block - red_block,
                        denom,
                        out=np.full_like(red_block, -9999, dtype=np.float32),
                        where=denom != 0
                    )
                    ndvi_block = np.nan_to_num(ndvi_block, nan=-9999.0, posinf=-9999.0, neginf=-9999.0)
                    dst.write(ndvi_block, 1, window=window)

        _log(f"تم حفظ NDVI في: {ndvi_path}")
        return ndvi_path

    def get_weather(self, lat: float, lon: float) -> dict:
        """جلب بيانات الطقس من Open-Meteo"""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "daily": ["temperature_2m_mean", "relative_humidity_2m_mean",
                      "precipitation_sum", "evapotranspiration_sum"],
            "timezone": "auto"
        }
        resp = self.session.get(OPEN_METEO_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def run(self) -> Optional[pathlib.Path]:
        """تنفيذ سير العمل بالكامل: بحث → تنزيل → حساب NDVI"""
        product = self.search()
        if not product:
            return None

        assets = product["assets"]
        red_href = assets.get("B04", {}).get("href")
        nir_href = assets.get("B08", {}).get("href")

        if not red_href or not nir_href:
            _log("روابط النطاقات غير متوفرة", "ERROR")
            return None

        red_path = self._download_band(red_href, "الأحمر B04")
        nir_path = self._download_band(nir_href, "تحت الحمراء B08")

        return self.compute_ndvi(red_path, nir_path)


# ----------------------------------------------------------------------
# للتشغيل المباشر
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ndvi_file = SentinelNDVI(
        aoi_geojson="data/area_of_interest.geojson",
        start_date="2026-01-01",
        end_date="2026-11-15"
    ).run()

    if ndvi_file:
        print(f"\n✅ تم إنشاء ملف NDVI: {ndvi_file.resolve()}")
    else:
        print("\n❌ لم يتم العثور على بيانات مناسبة")
