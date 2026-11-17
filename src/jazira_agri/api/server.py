from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..auth import create_session_token, validate_api_key, validate_credentials, verify_session_token
from ..core.configuration import get_settings
from ..core.database import DatabaseUnavailable, PostgresRepository
from ..core.engine import RecommendationStore
from ..knowledge.loader import load_syrian_crops, load_syrian_diseases, load_syrian_regions

app = FastAPI(title="JaziraAgri-OS", version="0.2.0")
SESSION_COOKIE = "jazira_session"
TEMPLATE = Path(__file__).resolve().parents[3] / "templates" / "index.html"


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


def current_user(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> str:
    settings = get_settings()
    if validate_api_key(x_api_key, settings.api_key):
        return "api-client"
    token = request.cookies.get(SESSION_COOKIE, "")
    payload = verify_session_token(token, settings.secret_key) if settings.secret_key else None
    if payload:
        return str(payload["sub"])
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    database_status = "not_configured"
    repository = PostgresRepository()
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
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="strict",
        max_age=28800,
        path="/",
    )
    return {"status": "authenticated", "username": payload.username.strip(), "knowledge_base": settings.default_knowledge}


@app.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "logged_out"}


@app.get("/api/knowledge")
def knowledge(_: str = Depends(current_user)) -> dict[str, Any]:
    return {
        "default": get_settings().default_knowledge,
        "crops": load_syrian_crops(),
        "regions": load_syrian_regions(),
        "diseases": load_syrian_diseases(),
    }


@app.get("/api/dashboard")
def dashboard(username: str = Depends(current_user)) -> dict[str, Any]:
    repository = PostgresRepository()
    db_state = "not_configured"
    if repository.configured:
        try:
            repository.health()
            db_state = "connected"
        except DatabaseUnavailable:
            db_state = "unavailable"
    return {
        "username": username,
        "database": db_state,
        "knowledge_base": get_settings().default_knowledge,
        "priority_crops": ["wheat", "barley", "cotton"],
        "priority_regions": ["tal_abyad", "raqqa"],
        "recent_recommendations": RecommendationStore(get_settings().log_dir + "/recommendations").recent(5),
    }


@app.post("/api/recommendations", status_code=status.HTTP_201_CREATED)
def save_recommendation(payload: RecommendationPayload, username: str = Depends(current_user)) -> dict[str, Any]:
    record = payload.model_dump()
    record["username"] = username
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    repository = PostgresRepository()
    if repository.configured:
        try:
            record["id"] = repository.save_recommendation(record)
            record["storage"] = "postgresql"
        except DatabaseUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        path = RecommendationStore(get_settings().log_dir + "/recommendations").append(record)
        record["storage"] = "local_jsonl"
        record["record"] = path.name
    return record
