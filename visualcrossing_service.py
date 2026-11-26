import requests
import os

API_KEY = os.getenv(
    "VISUAL_CROSSING_API_KEY"
)

BASE_URL = (
    "https://weather.visualcrossing.com/"
    "VisualCrossingWebServices/rest/services/timeline"
)

def current_weather(location):

    url = f"{BASE_URL}/{location}"

    params = {

        "unitGroup": "metric",

        "include": "current",

        "key": API_KEY,

        "contentType": "json"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    return response.json()


def forecast_weather(
    location,
    start_date,
    end_date
):

    url = (
        f"{BASE_URL}/"
        f"{location}/"
        f"{start_date}/"
        f"{end_date}"
    )

    params = {

        "unitGroup": "metric",

        "include": "days,hours",

        "elements":
        "datetime,tempmax,tempmin,temp,humidity,conditions",

        "key": API_KEY,

        "contentType": "json"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    return response.json()
