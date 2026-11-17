from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..advisor.farm_advice import build_farm_advice
from ..knowledge.loader import load_syrian_crops, load_syrian_diseases, load_syrian_regions

app = FastAPI(title="JaziraAgri-OS API", version="0.2.0")


class AdviceRequest(BaseModel):
    crop_id: str = Field(min_length=1, max_length=32)
    region_id: str = Field(min_length=1, max_length=64)
    inputs: dict[str, Any] = Field(default_factory=dict)


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
