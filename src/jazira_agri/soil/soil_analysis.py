class SoilAnalysis:
    TEXTURES = {
        "sandy": "رملية — تصريف سريع، تحتاج ري متكرر",
        "loam": "طينية رملية — توازن مثالي للمحاصيل",
        "clay": "طينية — غنية بالعناصر، تصريف بطيء"
    }

    @staticmethod
    def get_texture_type(sand, silt, clay):
        if sand > 70: return "sandy"
        elif clay > 40: return "clay"
        return "loam"

    @staticmethod
    def interpret_ph(ph):
        if ph < 5.5: return "حمضية — يفضل إضافة الجير الكلسي", True
        elif 5.5 <= ph <= 7.5: return "مثالية — لا حاجة لتعديل", False
        return "قلوية — يفضل إضافة كبريت زراعي", True
