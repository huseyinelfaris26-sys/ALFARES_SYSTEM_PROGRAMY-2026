from __future__ import annotations

import math
from typing import Any

from ..knowledge.loader import load_syrian_crops, load_syrian_regions

_MEASURE_FIELDS = (
    "seasonal_rain_mm",
    "irrigation_mm",
    "available_soil_water_mm",
    "crop_water_demand_mm",
)


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")
    return float(value)


def _validated_water_inputs(inputs: dict[str, Any]) -> dict[str, float]:
    missing = [key for key in _MEASURE_FIELDS if key not in inputs or inputs[key] is None]
    if missing:
        raise ValueError(f"missing scenario inputs: {', '.join(missing)}")
    return {key: _finite_nonnegative(inputs[key], key) for key in _MEASURE_FIELDS}


def simulate_water_scenarios(
    *,
    crop_id: str,
    region_id: str,
    baseline: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare explicitly supplied seasonal water assumptions.

    This is a transparent arithmetic scenario calculator, not a crop growth model.
    Rainfall and irrigation are treated as fully available and this simplification
    ignores runoff, drainage, timing, rooting depth, and crop coefficients. It
    deliberately produces no yield, risk probability, or irrigation prescription.
    """
    crops = load_syrian_crops()
    regions = load_syrian_regions()
    if crop_id not in crops:
        raise ValueError(f"unknown crop in Syrian knowledge base: {crop_id}")
    if region_id not in regions:
        raise ValueError(f"unknown region in Syrian knowledge base: {region_id}")
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be an object")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")
    if len(scenarios) > 20:
        raise ValueError("at most 20 scenarios are allowed")

    baseline_inputs = _validated_water_inputs(baseline)

    def calculate(name: str, values: dict[str, Any], is_baseline: bool) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError("each scenario requires a name of 1 to 80 characters")
        parsed = _validated_water_inputs(values)
        supply = parsed["seasonal_rain_mm"] + parsed["irrigation_mm"] + parsed["available_soil_water_mm"]
        demand = parsed["crop_water_demand_mm"]
        balance = supply - demand
        return {
            "name": name.strip(),
            "inputs": parsed,
            "assumed_total_water_supply_mm": round(supply, 2),
            "assumed_water_balance_mm": round(balance, 2),
            "arithmetic_water_shortfall_mm": round(max(0.0, -balance), 2),
            "change_vs_baseline": None if is_baseline else {
                "supply_delta_mm": round(supply - base_supply, 2),
                "balance_delta_mm": round(balance - base_balance, 2),
            },
        }

    base_supply = baseline_inputs["seasonal_rain_mm"] + baseline_inputs["irrigation_mm"] + baseline_inputs["available_soil_water_mm"]
    base_balance = base_supply - baseline_inputs["crop_water_demand_mm"]
    results = [calculate("baseline", baseline_inputs, True)]
    seen_names = {"baseline"}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("each scenario must be an object")
        name = scenario.get("name")
        if isinstance(name, str) and name.strip().casefold() in seen_names:
            raise ValueError(f"duplicate scenario name: {name}")
        result = calculate(name, scenario.get("inputs"), False)
        seen_names.add(result["name"].casefold())
        results.append(result)

    return {
        "crop": crop_id,
        "crop_ar": crops[crop_id].get("name_ar"),
        "region": region_id,
        "region_ar": regions[region_id].get("name_ar"),
        "simulation_type": "seasonal_water_balance_sensitivity",
        "status": "illustrative_assumption_only",
        "results": results,
        "yield_t_ha": None,
        "risk_probability": None,
        "confidence": None,
        "limitations": [
            "هذه مقارنة حسابية لمدخلات افتراضية وليست محاكاة نمو DSSAT أو APSIM.",
            "تفترض الحسابات أن المطر والري وماء التربة المدخل متاح بالكامل للنبات؛ لا تحسب الجريان أو الصرف أو توقيت الهطول.",
            "لا تنتج غلة أو احتمال مخاطر أو كمية ري موصى بها.",
            "استخدم قياسات حقلية ومصادر موثقة، وراجع النتائج مع مهندس زراعي محلي.",
        ],
        "knowledge_status": "draft_needs_local_validation",
    }
