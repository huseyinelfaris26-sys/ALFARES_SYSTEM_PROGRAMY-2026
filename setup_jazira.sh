#!/usr/bin/env bash
# JaziraAgri-OS setup. Run INSIDE the repo folder:  bash setup_jazira.sh
# Safe: it never overwrites an existing file (it writes NAME.new instead).
set -e

if [ ! -d .git ]; then
  echo "ERROR: run this inside the jazira-agri-os repo folder (the one that has .git)"
  exit 1
fi

put() {
  target="$1"
  mkdir -p "$(dirname "$target")"
  if [ -e "$target" ]; then
    target="$target.new"
    echo "exists, writing: $target"
  else
    echo "created: $target"
  fi
  cat > "$target"
}

mkdir -p data/regions data/knowledge data/photos/inbox data/logs tests
mkdir -p src/jazira_agri/core src/jazira_agri/knowledge src/jazira_agri/advisor src/jazira_agri/intelligence

# ---------- move the misspelled sync file to its right place ----------
if [ -f offlin_sync.py ]; then
  if [ -e src/jazira_agri/core/offline_sync.py ]; then
    echo "core/offline_sync.py already exists; leaving offlin_sync.py in place"
  else
    git mv offlin_sync.py src/jazira_agri/core/offline_sync.py
    echo "moved offlin_sync.py -> src/jazira_agri/core/offline_sync.py"
  fi
fi

# ---------- package markers ----------
for d in src/jazira_agri src/jazira_agri/core src/jazira_agri/knowledge src/jazira_agri/advisor src/jazira_agri/intelligence; do
  [ -e "$d/__init__.py" ] || { : > "$d/__init__.py"; echo "created: $d/__init__.py"; }
done

# ---------- pyproject ----------
put pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "jazira-agri-os"
version = "0.1.0"
description = "Offline-first agricultural AI for the Euphrates and Jazira basin"
requires-python = ">=3.11"
dependencies = ["Pillow>=10"]

[project.scripts]
jazira = "jazira_agri.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
EOF

# ---------- region data: Tal Abyad ----------
put data/regions/tal_abyad.json <<'EOF'
{
  "region": "tal_abyad",
  "name_ar": "تل أبيض",
  "name_en": "Tal Abyad",
  "rain_classes_mm": {
    "good_min": 250,
    "note": "ASSUMPTION: confirm the rainfall threshold with local records"
  },
  "water_sources": [
    {"id": "rain", "name_ar": "مطر (بعل)", "reliable": true},
    {"id": "solar_well", "name_ar": "بئر بطاقة شمسية", "reliable": true},
    {"id": "qarmukh_turmiya", "name_ar": "نهر قرموخ / ترميا", "reliable": false,
     "note": "supply is not stable, sometimes cut off, caused heavy farmer losses"}
  ],
  "areas": [
    {"id": "meryan_sharkrak", "name_ar": "من مريران حتى الشركراك", "farming": "rainfed",
     "soil": "red_clay", "crops": ["wheat", "barley", "cumin"]},
    {"id": "zanbaq", "name_ar": "الزنباق", "farming": "irrigated", "water": ["solar_well", "qarmukh_turmiya"]},
    {"id": "qaysariyah", "name_ar": "القيصرية", "farming": "irrigated", "water": ["solar_well", "qarmukh_turmiya"]},
    {"id": "ali_bahliyah", "name_ar": "علي باحلية", "farming": "irrigated", "water": ["solar_well", "qarmukh_turmiya"]},
    {"id": "sharkrak", "name_ar": "الشركراك", "farming": "irrigated", "water": ["solar_well", "qarmukh_turmiya"]}
  ],
  "yields": [
    {"crop": "wheat",  "farming": "irrigated", "condition": "good",    "low": 50, "high": 65, "unit": "q_per_ha", "source": "farmers", "confidence": "medium"},
    {"crop": "barley", "farming": "irrigated", "condition": "good",    "low": 50, "high": 65, "unit": "q_per_ha", "source": "farmers", "confidence": "medium"},
    {"crop": "wheat",  "farming": "rainfed",   "condition": "rain_good", "low": 20, "high": 35, "unit": "q_per_ha", "source": "farmers", "confidence": "medium"},
    {"crop": "barley", "farming": "rainfed",   "condition": "rain_good", "low": 20, "high": 35, "unit": "q_per_ha", "source": "farmers", "confidence": "medium"},
    {"crop": "wheat",  "farming": "rainfed",   "condition": "drought", "low": 2, "high": 10, "unit": "q_per_ha", "source": "farmers", "confidence": "medium"},
    {"crop": "barley", "farming": "rainfed",   "condition": "drought", "low": 2, "high": 10, "unit": "q_per_ha", "source": "farmers", "confidence": "medium"},
    {"crop": "wheat",  "farming": "rainfed",   "condition": "drought_best", "low": 12, "high": 12, "unit": "q_per_ha", "source": "farmers", "confidence": "low"},
    {"crop": "barley", "farming": "rainfed",   "condition": "drought_best", "low": 12, "high": 12, "unit": "q_per_ha", "source": "farmers", "confidence": "low"},
    {"crop": "barley", "farming": "unknown",   "condition": "exceptional", "low": 80, "high": 80, "unit": "q_per_ha", "source": "farmers", "confidence": "low",
     "note": "small plots (about 40 dunum), white barley"},
    {"crop": "wheat",  "farming": "unknown",   "condition": "exceptional", "low": 40, "high": 40, "unit": "q_per_ha", "source": "farmers", "confidence": "low",
     "note": "small plots (about 40 dunum), soft wheat"}
  ],
  "unit_confirmed": false,
  "unit_note": "The yield numbers were given without a unit. Assumed quintal per hectare (1 q/ha = 10 kg/dunum). If they are kg/dunum, change q_per_ha to kg_per_dunum in this file.",
  "crop_notes": {
    "cumin": "High cost and high risk, but the best income if the crop succeeds. No yield numbers collected yet."
  },
  "cost_per_dunum": null,
  "selling_price": null
}
EOF

# ---------- crops knowledge: seeds, rates, fertilizers ----------
put data/knowledge/crops.json <<'EOF'
{
  "_warning": "All values here are general starting points with verified=false. Confirm every seed variety, rate and dose with the local agricultural extension service and farmers, then set verified=true.",
  "wheat": {
    "name_ar": "قمح", "name_en": "Wheat", "verified": false,
    "seeds": [
      {"name": "Sham 6", "name_ar": "شام 6"},
      {"name": "Sham 8", "name_ar": "شام 8"},
      {"name": "Sham 10", "name_ar": "شام 10"}
    ],
    "seed_rate_kg_per_dunum": {"rainfed": [12, 15], "irrigated": [18, 22]},
    "ec_threshold_dsm": 6.0,
    "fertilizers": {
      "rainfed": [
        {"name_ar": "فوسفات ثنائي الأمونيوم DAP", "name_en": "DAP 18-46-0", "stage": "at sowing", "dose_kg_per_dunum": [8, 12]},
        {"name_ar": "يوريا 46%", "name_en": "Urea 46%", "stage": "tillering, only if rain is good", "dose_kg_per_dunum": [5, 10]}
      ],
      "irrigated": [
        {"name_ar": "فوسفات ثنائي الأمونيوم DAP", "name_en": "DAP 18-46-0", "stage": "at sowing", "dose_kg_per_dunum": [15, 20]},
        {"name_ar": "يوريا 46%", "name_en": "Urea 46%", "stage": "split: tillering and stem elongation", "dose_kg_per_dunum": [20, 30]}
      ]
    },
    "diseases": ["yellow_rust", "brown_rust", "powdery_mildew", "septoria", "loose_smut", "sunn_pest", "aphids"]
  },
  "barley": {
    "name_ar": "شعير", "name_en": "Barley", "verified": false,
    "seeds": [
      {"name": "Arabi Abiad", "name_ar": "عربي أبيض"},
      {"name": "Arabi Aswad", "name_ar": "عربي أسود"}
    ],
    "seed_rate_kg_per_dunum": {"rainfed": [10, 14], "irrigated": [15, 20]},
    "ec_threshold_dsm": 8.0,
    "fertilizers": {
      "rainfed": [
        {"name_ar": "فوسفات ثنائي الأمونيوم DAP", "name_en": "DAP 18-46-0", "stage": "at sowing", "dose_kg_per_dunum": [6, 10]}
      ],
      "irrigated": [
        {"name_ar": "فوسفات ثنائي الأمونيوم DAP", "name_en": "DAP 18-46-0", "stage": "at sowing", "dose_kg_per_dunum": [12, 18]},
        {"name_ar": "يوريا 46%", "name_en": "Urea 46%", "stage": "tillering", "dose_kg_per_dunum": [15, 22]}
      ]
    },
    "diseases": ["net_blotch", "powdery_mildew", "brown_rust", "aphids"]
  },
  "cumin": {
    "name_ar": "كمون", "name_en": "Cumin", "verified": false,
    "seeds": [
      {"name": "Local cumin", "name_ar": "كمون بلدي"}
    ],
    "seed_rate_kg_per_dunum": {"rainfed": [2, 4], "irrigated": [2, 4]},
    "ec_threshold_dsm": 3.0,
    "fertilizers": {
      "rainfed": [
        {"name_ar": "فوسفات ثنائي الأمونيوم DAP", "name_en": "DAP 18-46-0", "stage": "at sowing", "dose_kg_per_dunum": [5, 8]}
      ],
      "irrigated": [
        {"name_ar": "فوسفات ثنائي الأمونيوم DAP", "name_en": "DAP 18-46-0", "stage": "at sowing", "dose_kg_per_dunum": [8, 12]}
      ]
    },
    "diseases": ["fusarium_wilt", "alternaria_blight", "powdery_mildew"]
  }
}
EOF

# ---------- diseases knowledge ----------
put data/knowledge/diseases.json <<'EOF'
{
  "_warning": "Advisory only. Treatments name active-ingredient families, not brands. Always follow the product label and confirm with a local agronomist.",
  "symptoms": {
    "yellow_stripes": "خطوط صفراء متوازية على الورقة",
    "orange_pustules": "بثرات برتقالية أو صدئية اللون",
    "white_powder": "مسحوق أبيض على الأوراق",
    "brown_spots": "بقع بنية على الأوراق",
    "black_dots": "نقاط سوداء صغيرة داخل البقع",
    "yellowing": "اصفرار عام",
    "wilting": "ذبول النبات",
    "insect_seen": "حشرات ظاهرة على النبات",
    "sticky_leaves": "أوراق لزجة",
    "shriveled_grains": "حبوب مجعدة أو ضامرة",
    "white_heads": "سنابل بيضاء جافة",
    "black_heads": "سنابل سوداء مسودّة",
    "net_lines": "خطوط شبكية بنية على ورق الشعير",
    "root_rot": "تعفن الجذور"
  },
  "diseases": {
    "yellow_rust": {
      "name_ar": "الصدأ الأصفر", "name_en": "Yellow rust", "crops": ["wheat"],
      "symptoms": {"yellow_stripes": 3, "orange_pustules": 1, "yellowing": 1},
      "treatment_ar": "رش مبيد فطري من عائلة التريازول (مثل تيبوكونازول أو بروبيكونازول) عند ظهور الأعراض الأولى. أفضل وقاية: أصناف مقاومة وزراعة مبكرة معتدلة."
    },
    "brown_rust": {
      "name_ar": "الصدأ البني", "name_en": "Brown rust", "crops": ["wheat", "barley"],
      "symptoms": {"orange_pustules": 3, "yellowing": 1},
      "treatment_ar": "مبيد فطري من عائلة التريازول عند بداية الإصابة، ومراقبة الحقل في الربيع الدافئ الرطب."
    },
    "powdery_mildew": {
      "name_ar": "البياض الدقيقي", "name_en": "Powdery mildew", "crops": ["wheat", "barley", "cumin"],
      "symptoms": {"white_powder": 3, "yellowing": 1},
      "treatment_ar": "الكبريت القابل للبلل أو مبيد تريازول، وتجنب الإفراط في التسميد الآزوتي."
    },
    "septoria": {
      "name_ar": "تبقع الأوراق (سبتوريا)", "name_en": "Septoria leaf blotch", "crops": ["wheat"],
      "symptoms": {"brown_spots": 2, "black_dots": 2, "yellowing": 1},
      "treatment_ar": "مبيد تريازول، تدوير المحاصيل، وإزالة مخلفات الموسم السابق."
    },
    "loose_smut": {
      "name_ar": "التفحم السائب", "name_en": "Loose smut", "crops": ["wheat", "barley"],
      "symptoms": {"black_heads": 3},
      "treatment_ar": "لا علاج للنبات المصاب. المعالجة في الموسم القادم: تطهير البذور بمطهر جهازي مسجل، واستخدام بذار نظيف."
    },
    "sunn_pest": {
      "name_ar": "السونة", "name_en": "Sunn pest", "crops": ["wheat", "barley"],
      "symptoms": {"shriveled_grains": 3, "white_heads": 2, "insect_seen": 2},
      "treatment_ar": "الرش بمبيد حشري مسجل في مرحلة الحوريات (قبل البلوغ) وبالتنسيق مع الإرشاد الزراعي، لأن التوقيت هو العامل الحاسم."
    },
    "aphids": {
      "name_ar": "المن", "name_en": "Aphids", "crops": ["wheat", "barley"],
      "symptoms": {"insect_seen": 2, "sticky_leaves": 2, "yellowing": 1},
      "treatment_ar": "مراقبة العتبة الاقتصادية قبل الرش، ثم مبيد حشري مسجل مع الحفاظ على الأعداء الحيوية قدر الإمكان."
    },
    "net_blotch": {
      "name_ar": "التبقع الشبكي في الشعير", "name_en": "Net blotch", "crops": ["barley"],
      "symptoms": {"net_lines": 3, "brown_spots": 2},
      "treatment_ar": "تطهير البذور، تدوير المحاصيل، ومبيد تريازول عند الحاجة."
    },
    "fusarium_wilt": {
      "name_ar": "ذبول الفيوزاريوم", "name_en": "Fusarium wilt", "crops": ["cumin"],
      "symptoms": {"wilting": 3, "root_rot": 2, "yellowing": 1},
      "treatment_ar": "لا علاج بعد الإصابة. الوقاية: تدوير المحاصيل (عدم زراعة الكمون في نفس الأرض سنوات متتالية)، بذار نظيف مطهر، وتصريف جيد للماء."
    },
    "alternaria_blight": {
      "name_ar": "لفحة الألترناريا", "name_en": "Alternaria blight", "crops": ["cumin"],
      "symptoms": {"brown_spots": 3, "yellowing": 1},
      "treatment_ar": "إزالة المخلفات، مبيد فطري وقائي مسجل، وتجنب الرطوبة العالية والكثافة الزائدة."
    }
  }
}
EOF

# ---------- knowledge loader ----------
put src/jazira_agri/knowledge/loader.py <<'EOF'
"""Load JSON knowledge files. تحميل ملفات المعرفة.

The data folder is found automatically (repo/data) or via env JAZIRA_DATA.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def data_dir() -> Path:
    """Return the data folder. إرجاع مجلد البيانات."""
    env = os.environ.get("JAZIRA_DATA")
    if env:
        return Path(env)
    # this file: <repo>/src/jazira_agri/knowledge/loader.py
    return Path(__file__).resolve().parents[3] / "data"


def load_json(relative: str) -> dict[str, Any]:
    path = data_dir() / relative
    if not path.is_file():
        raise FileNotFoundError(f"missing data file: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_crops() -> dict[str, Any]:
    crops = load_json("knowledge/crops.json")
    return {k: v for k, v in crops.items() if not k.startswith("_")}


def load_diseases() -> dict[str, Any]:
    return load_json("knowledge/diseases.json")


def load_region(name: str) -> dict[str, Any]:
    return load_json(f"regions/{name}.json")
EOF

# ---------- recommend ----------
put src/jazira_agri/advisor/recommend.py <<'EOF'
"""Seed, fertilizer and expected-yield advice. نصائح البذور والأسمدة والإنتاج المتوقع."""
from __future__ import annotations

from typing import Any

from ..knowledge.loader import load_crops, load_region

_UNIT_TO_KG_PER_DUNUM = {"kg_per_dunum": 1.0, "q_per_ha": 10.0}


def classify_rain(region: dict[str, Any], rain_mm: float) -> str:
    """Rain-fed season class from seasonal rain in mm. تصنيف الموسم المطري."""
    return "rain_good" if rain_mm >= region["rain_classes_mm"]["good_min"] else "drought"


def recommend(
    crop: str,
    farming: str,
    region_name: str = "tal_abyad",
    rain_mm: float | None = None,
    water_ec: float | None = None,
) -> dict[str, Any]:
    """Build advice for one crop. إعداد التوصية لمحصول واحد."""
    crops = load_crops()
    region = load_region(region_name)
    if crop not in crops:
        raise ValueError(f"unknown crop '{crop}'. choices: {', '.join(crops)}")
    if farming not in ("rainfed", "irrigated"):
        raise ValueError("farming must be 'rainfed' or 'irrigated'")

    info = crops[crop]
    if farming == "irrigated":
        conditions = {"good"}
    elif rain_mm is None:
        conditions = {"rain_good", "drought", "drought_best"}
    else:
        cls = classify_rain(region, rain_mm)
        conditions = {"rain_good"} if cls == "rain_good" else {"drought", "drought_best"}

    yields = []
    for rec in region["yields"]:
        if rec["crop"] != crop or rec["farming"] != farming or rec["condition"] not in conditions:
            continue
        factor = _UNIT_TO_KG_PER_DUNUM[rec["unit"]]
        yields.append({
            "condition": rec["condition"],
            "kg_per_dunum": [rec["low"] * factor, rec["high"] * factor],
            "source": rec["source"],
            "confidence": rec["confidence"],
        })
    exceptions = [
        {"kg_per_dunum": [r["low"] * _UNIT_TO_KG_PER_DUNUM[r["unit"]], r["high"] * _UNIT_TO_KG_PER_DUNUM[r["unit"]]],
         "note": r.get("note", "")}
        for r in region["yields"] if r["crop"] == crop and r["condition"] == "exceptional"
    ]

    warnings: list[str] = []
    if not region.get("unit_confirmed", False):
        warnings.append("وحدة أرقام الإنتاج غير مؤكدة (افتراض: قنطار/هكتار). راجع data/regions/tal_abyad.json")
    if not info.get("verified", False):
        warnings.append("بيانات البذور والأسمدة غير موثقة بعد: أكدها مع الإرشاد الزراعي والمزارعين")
    if farming == "irrigated":
        warnings.append("مصدر الري من النهر غير ثابت وقد ينقطع: وفّر بديلاً (بئر/طاقة شمسية) قبل مراحل الحساسية")
    if water_ec is not None and water_ec > info["ec_threshold_dsm"]:
        warnings.append(
            f"ملوحة ماء الري ({water_ec} dS/m) أعلى من حد تحمل المحصول ({info['ec_threshold_dsm']}): خطر على الإنتاج"
        )
    if crop in region.get("crop_notes", {}):
        warnings.append(region["crop_notes"][crop])

    return {
        "crop": crop,
        "crop_ar": info["name_ar"],
        "farming": farming,
        "seeds": info["seeds"],
        "seed_rate_kg_per_dunum": info["seed_rate_kg_per_dunum"][farming],
        "fertilizers": info["fertilizers"][farming],
        "expected_yield": yields,
        "reported_exceptions": exceptions,
        "common_diseases": info["diseases"],
        "warnings": warnings,
    }
EOF

# ---------- diagnose (photo + symptoms) ----------
put src/jazira_agri/advisor/diagnose.py <<'EOF'
"""Crop problem diagnosis from a photo plus symptoms. تشخيص مشاكل المحصول من صورة وأعراض.

HONEST LIMITS: the colour analysis is a weak hint only. The reliable part is the
symptom list. A real trained model can be plugged in through ImageClassifier.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from ..knowledge.loader import data_dir, load_diseases

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
IMAGE_HINT_WEIGHT = 0.5


class ImageClassifier(Protocol):
    """Plug a trained model here. Return {disease_id: probability 0..1}."""

    def predict(self, path: Path) -> dict[str, float]: ...


def analyze_colors(path: Path) -> dict[str, float]:
    """Share of green/yellow/orange/brown/white pixels. نسب الألوان في الصورة."""
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        rgb.thumbnail((256, 256))
        data = rgb.convert("HSV").tobytes()
    counts = {"green": 0, "yellow": 0, "orange": 0, "brown": 0, "white": 0}
    total = len(data) // 3 or 1
    for i in range(0, len(data) - 2, 3):
        h, s, v = data[i], data[i + 1], data[i + 2]
        deg = h * 360 / 255
        if s < 30 and v > 200:
            counts["white"] += 1
        elif 70 <= deg <= 170 and s > 60:
            counts["green"] += 1
        elif 40 <= deg < 70 and s > 80 and v > 120:
            counts["yellow"] += 1
        elif 15 <= deg < 40 and s > 120 and v > 150:
            counts["orange"] += 1
        elif 15 <= deg < 40 and s > 60 and v <= 150:
            counts["brown"] += 1
    return {k: c / total for k, c in counts.items()}


def hints_from_colors(ratios: dict[str, float]) -> set[str]:
    hints: set[str] = set()
    if ratios["yellow"] > 0.15:
        hints.add("yellowing")
    if ratios["brown"] > 0.08:
        hints.add("brown_spots")
    if ratios["orange"] > 0.03:
        hints.add("orange_pustules")
    if ratios["white"] > 0.10:
        hints.add("white_powder")
    return hints


def _store_photo(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    inbox = data_dir() / "photos" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    dest = inbox / f"{digest}{path.suffix.lower()}"
    if not dest.exists():
        shutil.copy2(path, dest)
    return str(dest)


def diagnose(
    crop: str,
    symptoms: list[str],
    photo: Path | None = None,
    classifier: ImageClassifier | None = None,
) -> dict[str, Any]:
    """Rank likely problems. ترتيب المشاكل المحتملة."""
    kb = load_diseases()
    vocab = kb["symptoms"]
    unknown = [s for s in symptoms if s not in vocab]
    if unknown:
        raise ValueError(f"unknown symptoms: {unknown}. valid: {sorted(vocab)}")

    hints: set[str] = set()
    ratios: dict[str, float] = {}
    stored = None
    model_scores: dict[str, float] = {}
    if photo is not None:
        photo = Path(photo)
        if not photo.is_file():
            raise FileNotFoundError(f"photo not found: {photo}")
        if photo.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"photo must be one of {sorted(ALLOWED_SUFFIXES)}")
        ratios = analyze_colors(photo)
        hints = hints_from_colors(ratios) - set(symptoms)
        stored = _store_photo(photo)
        if classifier is not None:
            model_scores = classifier.predict(photo)

    results = []
    for disease_id, d in kb["diseases"].items():
        if crop not in d["crops"]:
            continue
        possible = sum(d["symptoms"].values())
        got = sum(w for s, w in d["symptoms"].items() if s in symptoms)
        got += sum(w * IMAGE_HINT_WEIGHT for s, w in d["symptoms"].items() if s in hints)
        score = min(got / possible, 1.0)
        if disease_id in model_scores:
            score = 0.5 * score + 0.5 * model_scores[disease_id]
        if score <= 0:
            continue
        results.append({
            "id": disease_id,
            "name_ar": d["name_ar"],
            "score": round(score, 2),
            "confidence": "medium" if score >= 0.6 else "low",
            "treatment_ar": d["treatment_ar"],
        })
    results.sort(key=lambda r: r["score"], reverse=True)

    out = {
        "crop": crop,
        "symptoms_used": symptoms,
        "image_hints": sorted(hints),
        "color_ratios": {k: round(v, 3) for k, v in ratios.items()},
        "stored_photo": stored,
        "candidates": results[:3],
        "disclaimer_ar": "هذا تشخيص أولي مساعد فقط وليس نهائياً. أرسل الصورة للمرشد الزراعي قبل أي رش.",
    }
    log = data_dir() / "logs" / "diagnoses.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": int(time.time()), **out}, ensure_ascii=False) + "\n")
    return out
EOF

# ---------- command line ----------
put src/jazira_agri/cli.py <<'EOF'
"""Command line: jazira crops | recommend | diagnose | symptoms."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .advisor.diagnose import diagnose
from .advisor.recommend import recommend
from .knowledge.loader import load_crops, load_diseases


def _show(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jazira")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("crops", help="list crops")
    sub.add_parser("symptoms", help="list valid symptom keys")

    r = sub.add_parser("recommend", help="seed, fertilizer and yield advice")
    r.add_argument("--crop", required=True)
    r.add_argument("--farming", required=True, choices=["rainfed", "irrigated"])
    r.add_argument("--region", default="tal_abyad")
    r.add_argument("--rain", type=float, help="seasonal rain in mm")
    r.add_argument("--ec", type=float, help="irrigation water EC in dS/m")

    d = sub.add_parser("diagnose", help="diagnose from photo and symptoms")
    d.add_argument("--crop", required=True)
    d.add_argument("--photo", type=Path)
    d.add_argument("--symptoms", default="", help="comma separated keys")

    a = p.parse_args(argv)
    try:
        if a.cmd == "crops":
            for key, c in load_crops().items():
                print(f"{key}: {c['name_ar']} / {c['name_en']}")
        elif a.cmd == "symptoms":
            for key, label in load_diseases()["symptoms"].items():
                print(f"{key}: {label}")
        elif a.cmd == "recommend":
            _show(recommend(a.crop, a.farming, a.region, a.rain, a.ec))
        elif a.cmd == "diagnose":
            syms = [s.strip() for s in a.symptoms.split(",") if s.strip()]
            _show(diagnose(a.crop, syms, a.photo))
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

# ---------- tests ----------
put tests/test_basic.py <<'EOF'
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from jazira_agri.advisor.diagnose import diagnose
from jazira_agri.advisor.recommend import recommend


class BasicTests(unittest.TestCase):
    def test_rainfed_good_wheat(self):
        res = recommend("wheat", "rainfed", rain_mm=300)
        low, high = res["expected_yield"][0]["kg_per_dunum"]
        self.assertEqual((low, high), (200.0, 350.0))

    def test_drought_barley(self):
        res = recommend("barley", "rainfed", rain_mm=100)
        self.assertTrue(all(y["condition"] != "rain_good" for y in res["expected_yield"]))

    def test_salinity_warning(self):
        res = recommend("cumin", "irrigated", water_ec=5.0)
        self.assertTrue(any("ملوحة" in w for w in res["warnings"]))

    def test_diagnose_symptoms(self):
        out = diagnose("wheat", ["yellow_stripes"])
        self.assertEqual(out["candidates"][0]["id"], "yellow_rust")

    def test_diagnose_photo(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "leaf.png"
            Image.new("RGB", (64, 64), (230, 200, 20)).save(p)
            out = diagnose("wheat", [], photo=p)
            self.assertIn("yellowing", out["image_hints"])


if __name__ == "__main__":
    unittest.main()
EOF

# ---------- gitignore (append only missing lines) ----------
touch .gitignore
for line in "data/photos/" "data/logs/" "__pycache__/" "*.egg-info/" ".venv/"; do
  grep -qxF "$line" .gitignore || echo "$line" >> .gitignore
done

echo
echo "DONE. Next steps:"
echo "  python -m venv .venv"
echo "  source .venv/bin/activate"
echo "  pip install -e ."
echo "  python -m unittest discover -s tests"
echo "  jazira recommend --crop wheat --farming rainfed --rain 300"
echo "  jazira diagnose --crop wheat --photo /path/to/leaf.jpg --symptoms yellow_stripes"
