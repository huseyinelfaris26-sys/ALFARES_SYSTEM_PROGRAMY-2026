"""Small, timeout-bounded Open-Meteo forecast client."""

from __future__ import annotations

import math
from typing import Any

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherForecast:
    """Fetch daily forecast data for a point; no API key is required."""

    def __init__(self, lat: float, lon: float, *, timeout: float = 15.0) -> None:
        if not math.isfinite(lat) or not -90 <= lat <= 90:
            raise ValueError("latitude must be finite and in [-90, 90]")
        if not math.isfinite(lon) or not -180 <= lon <= 180:
            raise ValueError("longitude must be finite and in [-180, 180]")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.lat = lat
        self.lon = lon
        self.timeout = timeout

    def get_7day(self) -> dict[str, Any] | None:
        """Return seven daily max/min temperatures and precipitation, or None on network/API errors."""
        try:
            response = requests.get(
                OPEN_METEO_URL,
                params={
                    "latitude": self.lat,
                    "longitude": self.lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "forecast_days": 7,
                    "timezone": "auto",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, TimeoutError, ValueError, OSError):
            return None
        return payload if isinstance(payload, dict) and isinstance(payload.get("daily"), dict) else None
