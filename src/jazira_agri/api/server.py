from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator

from ..advisor.farm_advice import build_farm_advice
from ..auth import create_session_token, validate_api_key, validate_credentials, verify_session_token
from ..core.configuration import get_settings
from ..core.database import DatabaseUnavailable, PostgresRepository
from ..core.engine import RecommendationStore
from ..core.farm_management import FarmRepository
from ..knowledge.loader import load_syrian_crops, load_syrian_diseases, load_syrian_regions

app = FastAPI(title="JaziraAgri-OS", version="0.3.0")
SESSION_COOKIE = "jazira_session"
TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "index.html"


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=512)


class RecommendationPayload(BaseModel):
    crop: str = Field(min_length=1, max_length=64)
    region: str = Field(min_length=1, max_length=64)
    inputs: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    recommendation: dict[str, Any]
    result: dict[str, Any] | None = None


class FarmPayload(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    region: str = Field(default="tal_abyad", min_length=1, max_length=64)
    owner: str = Field(default="", max_length=128)
    area_ha: float = Field(gt=0)
    notes: str = Field(default="", max_length=500)


class FieldPayload(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    crop: str = Field(default="wheat", min_length=1, max_length=64)
    soil_type: str = Field(default="", max_length=64)
    irrigation: str = Field(default="", max_length=32)
    area_ha: float = Field(gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: str = Field(default="active", max_length=32)

    @model_validator(mode="after")
    def coordinates_are_a_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be provided or both omitted")
        return self


class AdvicePayload(BaseModel):
    crop: str = Field(min_length=1, max_length=64)
    inputs: dict[str, Any] = Field(default_factory=dict)


def current_user(request: Request, x_api_key: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if validate_api_key(x_api_key, settings.api_key):
        return "api-client"
    token = request.cookies.get(SESSION_COOKIE, "")
    session = verify_session_token(token, settings.secret_key) if settings.secret_key else None
    if session:
        return str(session["sub"])
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def _postgres() -> PostgresRepository:
    repository = PostgresRepository()
    return repository


def _farms() -> FarmRepository:
    return FarmRepository()


def _list_farms() -> list[dict[str, Any]]:
    repository = _postgres()
    if repository.configured:
        return repository.list_farms()
    return _farms().list_farms()


def _list_fields(farm_id: str) -> list[dict[str, Any]]:
    repository = _postgres()
    if repository.configured:
        return repository.list_fields(farm_id)
    return _farms().list_fields(farm_id)


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    database_status = "not_configured"
    repository = _postgres()
    if repository.configured:
        try:
            repository.health()
            database_status = "ok"
        except DatabaseUnavailable:
            database_status = "unavailable"
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env, "database": database_status}


@app.get("/settings")
def settings_view(_: str = Depends(current_user)) -> dict[str, Any]:
    return get_settings().as_dict()


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    if not TEMPLATE.is_file():
        raise HTTPException(status_code=500, detail="Dashboard template is missing")
    return HTMLResponse(TEMPLATE.read_text(encoding="utf-8"))


@app.post("/login")
def login(payload: LoginPayload, response: Response) -> dict[str, str]:
    settings = get_settings()
    if not settings.secret_key or len(settings.secret_key) < 32:
        raise HTTPException(status_code=503, detail="Set SECRET_KEY to a random value of at least 32 characters")
    if not validate_credentials(payload.username.strip(), payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = create_session_token(payload.username.strip(), settings.secret_key)
    response.set_cookie(key=SESSION_COOKIE, value=token, httponly=True, secure=settings.app_env.lower() == "production", samesite="strict", max_age=28800, path="/")
    return {"status": "authenticated", "username": payload.username.strip(), "knowledge_base": settings.default_knowledge}


@app.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "logged_out"}


@app.get("/api/knowledge")
def knowledge(_: str = Depends(current_user)) -> dict[str, Any]:
    return {"default": get_settings().default_knowledge, "crops": load_syrian_crops(), "regions": load_syrian_regions(), "diseases": load_syrian_diseases()}


@app.get("/api/regions/map")
def regions_map(_: str = Depends(current_user)) -> dict[str, Any]:
    """Return only reviewed GeoJSON boundaries; null/unavailable regions are not fabricated."""
    regions = load_syrian_regions()
    features = []
    for key, region in regions.items():
        geometry = region.get("geometry")
        if geometry:
            features.append({"type": "Feature", "geometry": geometry, "properties": {"region_id": key, "name_ar": region.get("name_ar"), "boundary_source": region.get("administrative_boundary_source")}})
    return {"type": "FeatureCollection", "features": features, "unavailable_regions": [key for key, item in regions.items() if not item.get("geometry")], "note": "لا تتوفر حدود إدارية موثقة حالياً؛ لا تعرض هذه الاستجابة حدوداً تخمينية."}


@app.get("/api/dashboard")
def dashboard(username: str = Depends(current_user)) -> dict[str, Any]:
    repository = _postgres()
    db_state = "not_configured"
    if repository.configured:
        try:
            repository.health()
            db_state = "connected"
            farm_count, field_count = repository.dashboard_counts()
            farms = repository.list_farms()
        except DatabaseUnavailable:
            db_state, farm_count, field_count, farms = "unavailable", 0, 0, []
    else:
        farms = _farms().list_farms()
        farm_count = len(farms)
        field_count = sum(len(_farms().list_fields(farm["id"])) for farm in farms)
    return {"username": username, "database": db_state, "knowledge_base": get_settings().default_knowledge, "priority_crops": ["wheat", "barley", "cotton"], "priority_regions": ["tal_abyad", "raqqa"], "farm_count": farm_count, "field_count": field_count, "farms": farms[:100], "recent_recommendations": RecommendationStore(get_settings().log_dir + "/recommendations").recent(5), "recent_activity": _farms().recent_activity(5) if db_state != "connected" else []}


@app.get("/api/farms")
def list_farms(_: str = Depends(current_user)) -> list[dict[str, Any]]:
    try:
        return _list_farms()
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/farms", status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmPayload, username: str = Depends(current_user)) -> dict[str, Any]:
    try:
        repository = _postgres()
        record = repository.create_farm(payload.model_dump()) if repository.configured else _farms().create_farm(payload.model_dump())
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record["created_by"] = username
    return record


@app.get("/api/farms/{farm_id}/fields")
def list_fields(farm_id: str, _: str = Depends(current_user)) -> list[dict[str, Any]]:
    try:
        return _list_fields(farm_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/farms/{farm_id}/fields", status_code=status.HTTP_201_CREATED)
def create_field(farm_id: str, payload: FieldPayload, username: str = Depends(current_user)) -> dict[str, Any]:
    try:
        repository = _postgres()
        record = repository.create_field(farm_id, payload.model_dump()) if repository.configured else _farms().create_field(farm_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Farm not found") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record["created_by"] = username
    return record


@app.post("/api/farms/{farm_id}/advice", status_code=status.HTTP_201_CREATED)
def farm_advice(farm_id: str, payload: AdvicePayload, username: str = Depends(current_user)) -> dict[str, Any]:
    try:
        repository = _postgres()
        if repository.configured:
            farms = repository.list_farms()
            farm = next((item for item in farms if item["id"] == farm_id), None)
            fields = repository.list_fields(farm_id)
        else:
            farm = _farms().get_farm(farm_id)
            fields = _farms().list_fields(farm_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    if payload.crop not in {field.get("crop") for field in fields}:
        raise HTTPException(status_code=400, detail="Crop does not belong to a field in this farm")
    try:
        advice = build_farm_advice(crop_id=payload.crop, region_id=farm["region"], inputs=payload.inputs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    advice["farm_id"] = farm_id
    advice["username"] = username
    advice["created_at"] = datetime.now(timezone.utc).isoformat()
    saved = {"username": username, "crop": payload.crop, "region": farm["region"], "inputs": {**payload.inputs, "farm_id": farm_id}, "confidence": 0.0, "recommendation": advice, "result": None}
    try:
        if repository.configured:
            advice["record_id"] = repository.save_recommendation(saved)
            advice["storage"] = "postgresql"
        else:
            advice["storage"] = "local_jsonl"
            RecommendationStore(get_settings().log_dir + "/recommendations").append(saved)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return advice


@app.get("/api/farms/{farm_id}/report")
def farm_report(farm_id: str, _: str = Depends(current_user)) -> dict[str, Any]:
    try:
        repository = _postgres()
        if repository.configured:
            report = repository.farm_report(farm_id)
        else:
            recommendations = RecommendationStore(get_settings().log_dir + "/recommendations").recent(100, farm_id=farm_id)
            report = _farms().report(farm_id, recommendations)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    return report


@app.get("/api/farms/{farm_id}/report.csv")
def farm_report_csv(farm_id: str, _: str = Depends(current_user)) -> StreamingResponse:
    try:
        repository = _postgres()
        report = repository.farm_report(farm_id) if repository.configured else _farms().report(farm_id, RecommendationStore(get_settings().log_dir + "/recommendations").recent(100, farm_id=farm_id))
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if report is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["farm", "field", "crop", "soil", "irrigation", "area_ha", "latitude", "longitude"])
    for field in report["fields"]:
        writer.writerow([report["farm"]["name"], field.get("name"), field.get("crop"), field.get("soil_type"), field.get("irrigation"), field.get("area_ha"), field.get("latitude"), field.get("longitude")])
    output.seek(0)
    return StreamingResponse(iter(["\ufeff" + output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=farm-{farm_id}-report.csv"})


@app.post("/api/recommendations", status_code=status.HTTP_201_CREATED)
def save_recommendation(payload: RecommendationPayload, username: str = Depends(current_user)) -> dict[str, Any]:
    record = payload.model_dump()
    record["username"] = username
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    repository = _postgres()
    try:
        if repository.configured:
            record["id"] = repository.save_recommendation(record)
            record["storage"] = "postgresql"
        else:
            path = RecommendationStore(get_settings().log_dir + "/recommendations").append(record)
            record["storage"] = "local_jsonl"
            record["record"] = path.name
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return record
