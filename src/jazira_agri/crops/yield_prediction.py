class YieldPredictor:
    def estimate(self, crop_id, area_m2, ndvi_avg=0.7, water_sufficient=True):
        refs = {"wheat": 0.5, "barley": 0.4, "cotton": 0.35, "olive": 0.18}
        base = refs.get(crop_id, 0.3)
        factor = ndvi_avg * (1.2 if water_sufficient else 0.7)
        tons = (area_m2 / 10000) * base * factor
        return round(tons, 2)
