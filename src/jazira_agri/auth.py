from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

_PBKDF2_ROUNDS = 600_000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a salted PBKDF2-SHA256 password hash suitable for an env var or database."""
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, rounds_text, salt_text, expected_text = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        if not 100_000 <= rounds <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt_text), rounds)
        return hmac.compare_digest(actual, _unb64(expected_text))
    except (ValueError, TypeError):
        return False


def validate_credentials(username: str, password: str) -> bool:
    """Validate configured account; prefer salted password hashes over legacy plain text."""
    from .core.configuration import get_settings

    settings = get_settings()
    if not settings.username or not username or not password:
        return False
    if not hmac.compare_digest(username, settings.username):
        return False
    if settings.password_hash:
        return verify_password(password, settings.password_hash)
    # Backward compatibility only. Set JAZIRA_PASSWORD_HASH for real deployments.
    return bool(settings.password) and hmac.compare_digest(password, settings.password)


def create_session_token(username: str, secret: str, ttl_seconds: int = 28800) -> str:
    payload = json.dumps(
        {"sub": username, "exp": int(time.time()) + ttl_seconds}, separators=(",", ":")
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
