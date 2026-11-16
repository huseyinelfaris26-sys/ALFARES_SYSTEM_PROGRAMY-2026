import requests

class WeatherForecast:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    def get_7day(self):
        url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
        try:
            resp = requests.get(url, timeout=15)
            return resp.json() if resp.ok else None
        except Exception:
            return None
