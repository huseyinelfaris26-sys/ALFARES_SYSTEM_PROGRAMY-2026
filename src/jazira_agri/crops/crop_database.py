class CropDatabase:
    def __init__(self):
        self.crops = {
            "wheat": {"name": "قمح", "cycle_days": 120, "water_per_m2": 450, "temp_min": 5, "temp_opt": 20},
            "barley": {"name": "شعير", "cycle_days": 110, "water_per_m2": 350, "temp_min": 4, "temp_opt": 18},
            "cotton": {"name": "قطن", "cycle_days": 160, "water_per_m2": 700, "temp_min": 15, "temp_opt": 28},
            "olive": {"name": "زيتون", "cycle_days": 365, "water_per_m2": 250, "temp_min": -5, "temp_opt": 22},
            "tomato": {"name": "طماطم", "cycle_days": 90, "water_per_m2": 400, "temp_min": 12, "temp_opt": 25}
        }

    def get_info(self, crop_id):
        return self.crops.get(crop_id.lower(), None)

    def list_all(self):
        return [(k, v["name"]) for k, v in self.crops.items()]
