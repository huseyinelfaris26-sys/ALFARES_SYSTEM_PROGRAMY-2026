from datetime import datetime, timedelta

class GrowthStage:
    STAGES = {
        "wheat": ["إنبات", "شتاء", "تفريع", "سنبلة", "نضج"],
        "cotton": ["إنبات", "أوراق", "براعم", "إزهار", "نضج"]
    }

    def get_current_stage(self, crop_id, plant_date):
        db = {
            "wheat": [0, 25, 60, 90, 110],
            "cotton": [0, 30, 60, 90, 140]
        }
        stages = self.STAGES.get(crop_id, ["نمو", "نضج"])
        days_passed = (datetime.now() - plant_date).days
        days_thresholds = db.get(crop_id, [0, 50, 100])
        for i, d in enumerate(reversed(days_thresholds)):
            if days_passed >= d:
                return stages[len(stages)-1 - i], days_passed
        return stages[0], days_passed
