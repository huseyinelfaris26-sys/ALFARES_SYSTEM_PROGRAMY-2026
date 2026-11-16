"""جدولة الري الذكي"""
from datetime import datetime, timedelta
import json

class IrrigationScheduler:
    def __init__(self, config_path="config/regions_syria_ne.json"):
        self.zones = {}
        self.load_config(config_path)

    def load_config(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.zones = json.load(f)
        except FileNotFoundError:
            pass

    def calculate_schedule(self, zone_id, soil_moisture, forecast_rain=0.0):
        now = datetime.now()
        if soil_moisture > 70 or forecast_rain > 5:
            return {"need_water": False, "next_check": now + timedelta(hours=6)}
        duration = max(5, int((60 - soil_moisture) * 0.8))
        return {
            "need_water": True,
            "start_time": now + timedelta(minutes=5),
            "duration_minutes": duration,
            "volume_liters": duration * 2.5
        }
