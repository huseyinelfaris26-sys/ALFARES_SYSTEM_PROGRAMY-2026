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
