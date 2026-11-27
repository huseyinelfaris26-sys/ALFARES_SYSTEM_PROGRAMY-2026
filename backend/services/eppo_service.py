import os
import requests

BASE_URL = (
    "https://api.eppo.int/gd/v2"
)

API_KEY = os.getenv(
    "EPPO_API_KEY"
)

HEADERS = {

    "Accept":
    "application/json",

    "X-Api-Key":
    API_KEY
}


def search_name(name):

    response = requests.get(

        f"{BASE_URL}/tools/name2codes",

        headers=HEADERS,

        params={

            "name": name,

            "onlyPreferred": True
        },

        timeout=30
    )

    return response.json()
