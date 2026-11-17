from __future__ import annotations

from typing import Any


def pest_record(pest_id: str) -> dict[str, Any]:
    from ..knowledge.loader import load_syrian_diseases

    catalog = load_syrian_diseases()
    record = catalog.get(pest_id)
    if not record or record.get("category") != "insect_pest":
        raise ValueError(f"unknown pest in Syrian catalog: {pest_id}")
    return record


def scouting_checklist(pest_id: str) -> dict[str, Any]:
    record = pest_record(pest_id)
    return {"pest_id": pest_id, "name_ar": record.get("name_ar"), "status": "needs_local_validation", "monitoring_protocol": record.get("monitoring_protocol"), "economic_threshold": record.get("economic_threshold"), "note": "No pesticide treatment or economic threshold is inferred."}
