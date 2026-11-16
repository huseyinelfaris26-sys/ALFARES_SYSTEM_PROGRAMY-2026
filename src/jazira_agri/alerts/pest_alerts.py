class PestAlert:
    CONDITIONS = {
        "locust": {"temp_min": 20, "humidity_min": 60, "rain_days": 0},
        "mildew": {"humidity_min": 85, "temp_range": [10, 22]}
    }

    @classmethod
    def check_risk(cls, pest, temp_avg, humidity, rain_last_7days):
        c = cls.CONDITIONS.get(pest)
        if not c: return False, "غير معروف"
        if pest == "locust":
            risk = temp_avg >= c["temp_min"] and humidity >= c["humidity_min"] and rain_last_7days <= c["rain_days"]
            return risk, "خطر عالي لغزو الجراد — بلّغ الجهات المختصة!" if risk else "خطر منخفض للجراد"
        if pest == "mildew":
            risk = humidity >= c["humidity_min"] and c["temp_range"][0] <= temp_avg <= c["temp_range"][1]
            return risk, "خطر عالي للعفن — تجنب الري بالرذاذ" if risk else "خطر منخفض للعفن"
        return False, ""
