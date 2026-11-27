from fastapi import APIRouter

from services.weather_service import (
    get_weather
)

router = APIRouter()


@router.get("/weather")
def weather():

    return get_weather()
