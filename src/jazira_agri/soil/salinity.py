class SalinityChecker:
    @staticmethod
    def check(ec_ds_m):
        if ec_ds_m < 2:
            return "منخفضة — آمنة لجميع المحاصيل", []
        elif ec_ds_m < 4:
            return "متوسطة — تجنب المحاصيل الحساسة", ["خس", "فاصولياء"]
        elif ec_ds_m < 8:
            return "عالية — محاصيل متحملة فقط", ["قمح", "شعير", "قطن"]
        return "عالية جداً — تحتاج لغسيل للتربة", ["شعير ملحي"]
