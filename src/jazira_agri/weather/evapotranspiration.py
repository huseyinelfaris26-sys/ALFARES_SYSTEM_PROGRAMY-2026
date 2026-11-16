class Evapotranspiration:
    @staticmethod
    def hargreaves(t_min, t_max, t_mean, ra=None):
        """حساب التبخر النتح بطريقة هارغريفز"""
        et0 = 0.0023 * (t_mean + 17.8) * ((t_max - t_min) ** 0.5) * (0.16)
        return round(et0, 2)
