from __future__ import annotations

from typing import Any

try:
    from fastapi import FastAPI
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is not installed. Install the API extras with: python -m pip install -e '.[api]'"
    ) from exc

from ..core.configuration import get_settings

app = FastAPI(title="JaziraAgri-OS", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "app": "JaziraAgri-OS", "environment": get_settings().app_env}


@app.get("/settings")
def settings() -> dict[str, Any]:
    return get_settings().as_dict()


@app.get("/")
def root() -> dict[str, Any]:
    return {"message": "JaziraAgri-OS API", "knowledge_base": get_settings().default_knowledge}
