class FertilizerAdvisor:
    RECOMMEND = {
        "wheat": {"N": 120, "P": 60, "K": 60, "unit": "كغم/هكتار"},
        "cotton": {"N": 150, "P": 80, "K": 50, "unit": "كغم/هكتار"},
        "olive": {"N": 80, "P": 40, "K": 100, "unit": "كغم/هكتار"}
    }

    def get_advice(self, crop_id, area_m2, n_status="adequate", p_status="adequate"):
        rec = dict(self.RECOMMEND.get(crop_id, {"N": 80, "P": 40, "K": 40, "unit": "كغم/هكتار"}))
        factor = area_m2 / 10000
        if n_status == "low": rec["N"] *= 1.3
        if p_status == "low": rec["P"] *= 1.4
        return {k: (round(v * factor, 2) if k != "unit" else v) for k, v in rec.items()}
