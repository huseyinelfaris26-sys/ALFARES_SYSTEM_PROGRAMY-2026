from datetime import datetime

class FrostAlert:
    @staticmethod
    def check(t_min, forecast_date=None):
        date = forecast_date or datetime.now().strftime("%Y-%m-%d")
        if t_min <= 0:
            return True, f"⚠️ تحذير صقيع: درجة الحرارة المتوقعة {t_min}° مئوية في {date} — غطِّ المحاصيل أو استخدم مراوح التدفئة"
        elif t_min <= 3:
            return False, f"تنبيه: درجات الحرارة منخفضة {t_min}° مئوية — راقب المحاصيل"
        return False, "درجات الحرارة آمنة"
