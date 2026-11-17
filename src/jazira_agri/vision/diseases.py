from __future__ import annotations

from typing import Any


def disease_catalog() -> dict[str, Any]:
    from ..knowledge.loader import load_syrian_diseases

    return load_syrian_diseases()


def disease_record(disease_id: str) -> dict[str, Any]:
    catalog = disease_catalog()
    if disease_id not in catalog:
        raise ValueError(f"unknown disease in Syrian catalog: {disease_id}")
    return catalog[disease_id]
