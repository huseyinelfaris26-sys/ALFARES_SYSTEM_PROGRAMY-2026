from __future__ import annotations

import math
from typing import Any


class WeatherForecast:
    """Small optional forecast client using Open-Meteo's public forecast endpoint."""

    def __init__(self, base_url: str = "https://api.open-meteo.com/v1/forecast") -> None:
        self.base_url = base_url

    def get_7day(self, latitude: float, longitude: float) -> dict[str, Any]:
        if not math.isfinite(latitude) or not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not math.isfinite(longitude) or not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install requests to use weather forecast: pip install requests") from exc
        response = requests.get(self.base_url, params={"latitude": latitude, "longitude": longitude, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum", "forecast_days": 7, "timezone": "auto"}, timeout=15)
        response.raise_for_status()
        return response.json()
