from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..auth import build_auth_payload
from ..core.configuration import get_settings

app = FastAPI(title="JaziraAgri-OS", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {"status": "ok", "app": "JaziraAgri-OS", "environment": settings.app_env}


@app.get("/settings")
def settings() -> dict[str, Any]:
    return get_settings().as_dict()


@app.get("/")
def root() -> HTMLResponse:
    from pathlib import Path

    template = Path(__file__).resolve().parents[2] / "templates" / "index.html"
    return HTMLResponse(template.read_text(encoding="utf-8"))


@app.post("/login")
def login(payload: dict[str, str]) -> dict[str, Any]:
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    auth = build_auth_payload(username, password)
    if not auth["valid"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {
        "status": "authenticated",
        "username": auth["username"],
        "knowledge_base": auth["knowledge_base"],
        "api_key": auth["api_key"],
    }


@app.get("/knowledge")
def knowledge() -> dict[str, Any]:
    return {
        "default": get_settings().default_knowledge,
        "available": ["general", "syrian"],
        "priority": ["wheat", "barley", "cotton"],
        "regions": ["tal_abyad", "raqqa"],
    }


@app.get("/")
def root_json() -> dict[str, Any]:
    return {"message": "JaziraAgri-OS API", "knowledge_base": get_settings().default_knowledge}
