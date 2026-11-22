import json
from pathlib import Path

# الوصول الصحيح للجذر الرئيسي للمشروع (3 مستويات للأعلى من ui/data_bridge.py)
BASE_DIR = Path(__file__).resolve().parents

def load_json_safe(relative_path: str, default=None):
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default if default is not None else {}
    return default if default is not None else {}

def get_regions():
    data = load_json_safe("config/regions_syria_ne.json", {})
    if isinstance(data, dict) and "regions" in data and data["regions"]:
        return list(data["regions"].keys())
    return ["تل أبيض", "الرقة", "الحسكة", "دير الزور", "الطبقة", "القامشلي"]

def get_crops():
    crops_db = load_json_safe("data/crops_database.json", {})
    crops_k = load_json_safe("data/knowledge/crops.json", {})
    if isinstance(crops_db, dict) and crops_db:
        return list(crops_db.keys())
    if isinstance(crops_k, dict) and crops_k:
        return list(crops_k.keys())
    return ["قمح (قاسي/طري)", "قطن", "شعير", "ذرة صفراء", "كمون"]

def get_soil_profiles():
    soils = load_json_safe("data/soil_profiles.json", {})
    if isinstance(soils, dict) and soils:
        return list(soils.keys())
    return ["تربة طينية ثقيلة", "تربة مزيجية (حوض الفرات)", "تربة رملية", "تربة متملحة"]

def get_diseases():
    return load_json_safe("data/knowledge/diseases.json", {
        "صدأ القمح الأصفر": "يظهر كبثور صفراء مرتبة في خطوط طولية على الأوراق. المكافحة: رش مبيد فطري مناسب وتجنب الإفراط في التسميد الآزوتي.",
        "دودة لوز القطن": "تصيب البراعم واللوز الصغير. المكافحة: المصائد الفرمونية والمكافحة الحيوية أو الكيميائية الموجهة.",
        "السونة": "حشرة ثاقبة ماصة تصيب سنابل القمح وتؤثر على جودة الغلوتين."
    })
