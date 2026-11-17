from __future__ import annotations

from datetime import date
from typing import Any

from ..knowledge.loader import load_syrian_crops, load_syrian_regions


def build_farm_advice(
    *,
    crop_id: str,
    region_id: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Build a transparent data-readiness/advice checklist, not an unvalidated prescription."""
    crops = load_syrian_crops()
    regions = load_syrian_regions()
    if crop_id not in crops:
        raise ValueError(f"unknown crop in Syrian knowledge base: {crop_id}")
    if region_id not in regions:
        raise ValueError(f"unknown Syrian priority region: {region_id}")

    crop = crops[crop_id]
    region = regions[region_id]
    required_by_crop = {
        "wheat": ["variety_id", "sowing_date", "soil_texture", "soil_test", "seasonal_rain_mm", "rain_distribution", "growth_stage"],
        "barley": ["variety_id", "sowing_date", "soil_texture", "soil_test", "seasonal_rain_mm", "rain_distribution", "growth_stage", "intended_use"],
        "cotton": ["variety_id", "sowing_date", "soil_texture", "soil_test", "irrigation_water_and_availability", "growth_stage", "pest_observations"],
    }
    required = required_by_crop[crop_id]
    missing = [key for key in required if inputs.get(key) in (None, "", [])]

    sowing_date = inputs.get("sowing_date")
    if sowing_date:
        try:
            date.fromisoformat(str(sowing_date))
        except ValueError as exc:
            raise ValueError("sowing_date must use YYYY-MM-DD format") from exc

    evidence_gaps = []
    if crop.get("knowledge_status") != "verified":
        evidence_gaps.append("قاعدة المحصول ما زالت مسودة ولم تعتمد محلياً")
    if region.get("geometry") is None:
        evidence_gaps.append("حدود المنطقة المكانية لم تُحمّل أو تُتحقق بعد")
    if region.get("local_weather", {}).get("status") != "available":
        evidence_gaps.append("لا توجد سلسلة طقس محلية موثقة ضمن قاعدة المنطقة")
    soil = region.get("soil", {})
    if soil.get("status") != "available":
        evidence_gaps.append("لا توجد نتائج عينة تربة محلية مرتبطة بهذا الحقل")

    return {
        "crop": crop_id,
        "crop_ar": crop.get("name_ar"),
        "region": region_id,
        "region_ar": region.get("name_ar"),
        "status": "data_collection_only" if missing or evidence_gaps else "needs_agronomist_review",
        "confidence": 0.0,
        "confidence_note": "لم تُعاير توصيات محلية أو نماذج إنتاج موثقة؛ لذلك لا تُحسب ثقة زراعية بعد.",
        "inputs_received": inputs,
        "missing_inputs": missing,
        "evidence_gaps": evidence_gaps,
        "next_steps": [
            "أضف بيانات الحقل وتحليل التربة مع المصدر والتاريخ والوحدات.",
            "وثّق الصنف وموسم الزراعة ومشاهدات المطر والمرحلة الحالية.",
            "راجع المعلومات مع مهندس زراعي محلي قبل تنفيذ أي إجراء أو جرعة.",
        ],
        "advice": "لا تصدر هذه النسخة جرعات سماد أو ري أو مبيدات أو أرقام إنتاج؛ البيانات السورية ما زالت غير متحققة.",
        "knowledge_base": "syrian_specialized_crops",
        "knowledge_status": "draft_needs_local_validation",
    }
