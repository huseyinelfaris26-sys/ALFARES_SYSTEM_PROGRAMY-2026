#!/usr/bin/env python3
"""Create a private local .env file without putting secrets in source control."""
from __future__ import annotations

import getpass
import secrets
from pathlib import Path

from jazira_agri.auth import hash_password


def main() -> int:
    target = Path(".env")
    if target.exists():
        answer = input(".env already exists. Replace it? [y/N] ").strip().lower()
        if answer != "y":
            print("Kept existing .env")
            return 0
    username = input("Admin username [admin]: ").strip() or "admin"
    while True:
        password = getpass.getpass("Admin password (minimum 12 characters): ")
        confirmation = getpass.getpass("Repeat password: ")
        if password != confirmation:
            print("Passwords do not match. Try again.")
            continue
        try:
            password_hash = hash_password(password)
            break
        except ValueError as exc:
            print(exc)
    db_password = secrets.token_urlsafe(32)
    lines = [
        "APP_NAME=JaziraAgri-OS",
        "APP_ENV=development",
        f"JAZIRA_USERNAME={username}",
        f"JAZIRA_PASSWORD_HASH={password_hash}",
        f"API_KEY={secrets.token_urlsafe(40)}",
        f"SECRET_KEY={secrets.token_urlsafe(48)}",
        "DEFAULT_KNOWLEDGE=syrian",
        "DB_HOST=localhost",
        "DB_PORT=5432",
        "DB_NAME=jazira_agri",
        "DB_USER=jazira",
        f"DB_PASSWORD={db_password}",
        "DATABASE_URL=",
        "LOG_DIR=data/logs",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    print("Created .env with generated API/database/session secrets and a salted password hash.")
    print("Store the database password printed in .env securely; it is not shown here.")
    print("For Docker Compose, DB_HOST is set to db by the compose environment override.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
