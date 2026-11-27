import requests

def get_weather():

    url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    params = {

        "latitude": 35.33,

        "longitude": 40.15,

        "hourly": [

            "temperature_2m",

            "precipitation",

            "soil_moisture_2_to_8cm"
        ],

        "forecast_days": 7
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    return response.json()
