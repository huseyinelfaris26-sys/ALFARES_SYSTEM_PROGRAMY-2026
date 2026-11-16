"""قراءة وتفسير رطوبة التربة"""
class SoilMoisture:
    @staticmethod
    def interpret(value, soil_type="loam"):
        if soil_type == "sandy":
            low, high = 15, 25
        elif soil_type == "clay":
            low, high = 35, 45
        else:
            low, high = 25, 35
        if value < low:
            return "جاف جداً — ري عاجل مطلوب", True
        elif value < high:
            return "جاف — يفضل قريباً", False
        return "رطب — حالة ممتازة", False
