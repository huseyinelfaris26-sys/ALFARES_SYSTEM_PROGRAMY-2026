from fastapi import APIRouter

from services.visualcrossing_service import (
    current_weather,
    forecast_weather
)

router = APIRouter()
