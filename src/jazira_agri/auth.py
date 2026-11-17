from __future__ import annotations

import hashlib
from typing import Any

from .core.configuration import get_settings


def hash_password(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


def validate_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    if username != settings.username:
        return False
    if not password:
        return False
    return hash_password(password) == hash_password(settings.password)


def generate_api_key() -> str:
    import secrets

    return secrets.token_urlsafe(32)


def build_auth_payload(username: str, password: str) -> dict[str, Any]:
    settings = get_settings()
    valid = validate_credentials(username, password)
    return {
        "valid": valid,
        "username": username if valid else None,
        "knowledge_base": settings.default_knowledge if valid else None,
        "api_key": settings.api_key if valid and settings.api_key else generate_api_key() if valid else None,
        "status": "authenticated" if valid else "invalid_credentials",
    }
