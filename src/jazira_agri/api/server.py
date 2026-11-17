from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..advisor.farm_advice import build_farm_advice
from ..knowledge.loader import load_syrian_crops, load_syrian_diseases, load_syrian_regions
from ..prediction.scenarios import simulate_water_scenarios

app = FastAPI(title="JaziraAgri-OS API", version="0.3.0")


class AdviceRequest(BaseModel):
    crop_id: str = Field(min_length=1, max_length=32)
    region_id: str = Field(min_length=1, max_length=64)
    inputs: dict[str, Any] = Field(default_factory=dict)


class ScenarioRequest(BaseModel):
    crop_id: str = Field(min_length=1, max_length=32)
    region_id: str = Field(min_length=1, max_length=64)
    baseline: dict[str, Any]
    scenarios: list[dict[str, Any]] = Field(min_length=1, max_length=20)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "knowledge": "syrian_specialized_draft"}


@app.get("/api/knowledge/crops")
def crops() -> dict[str, Any]:
    return load_syrian_crops()


@app.get("/api/knowledge/regions")
def regions() -> dict[str, Any]:
    return load_syrian_regions()


@app.get("/api/knowledge/diseases")
def diseases() -> dict[str, Any]:
    return load_syrian_diseases()


@app.post("/api/advice")
def advice(payload: AdviceRequest) -> dict[str, Any]:
    try:
        return build_farm_advice(crop_id=payload.crop_id, region_id=payload.region_id, inputs=payload.inputs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/scenarios/simulate")
def simulate_scenarios(payload: ScenarioRequest) -> dict[str, Any]:
    """Compare supplied water-balance assumptions; no yield prediction is implied."""
    try:
        return simulate_water_scenarios(
            crop_id=payload.crop_id,
            region_id=payload.region_id,
            baseline=payload.baseline,
            scenarios=payload.scenarios,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
