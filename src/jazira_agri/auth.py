from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def validate_credentials(username: str, password: str) -> bool:
    """Compare credentials against environment configuration without storing plaintext."""
    from .core.configuration import get_settings

    settings = get_settings()
    if not settings.username or not settings.password or not username or not password:
        return False
    return hmac.compare_digest(username, settings.username) and hmac.compare_digest(
        password, settings.password
    )


def create_session_token(username: str, secret: str, ttl_seconds: int = 28800) -> str:
    payload = json.dumps(
        {"sub": username, "exp": int(time.time()) + ttl_seconds},
        separators=(",", ":"),
    ).encode("utf-8")
    body = _b64(payload)
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def verify_session_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(body))
        if not isinstance(payload, dict) or not isinstance(payload.get("sub"), str):
            return None
        if not isinstance(payload.get("exp"), int) or payload["exp"] <= int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def validate_api_key(candidate: str | None, configured: str) -> bool:
    return bool(candidate and configured and hmac.compare_digest(candidate, configured))
