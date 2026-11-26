from fastapi import APIRouter

from services.visualcrossing_service import (
    current_weather,
    forecast_weather
)

router = APIRouter()

@router.get(
    "/weather/current"
)
def weather_current():
    return current_weather(
        "Deir ez-Zor,Syria"
    )

@router.get(
    "/weather/forecast"
)
def weather_forecast():
    return forecast_weather(
        "Deir ez-Zor,Syria",
        "2026-10-01",
        "2026-10-07"
    )
