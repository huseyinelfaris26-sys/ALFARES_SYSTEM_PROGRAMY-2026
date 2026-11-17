from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> None:
        return None

load_dotenv()


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "JaziraAgri-OS"
    app_env: str = "development"
    username: str = ""
    password: str = ""
    api_key: str = ""
    secret_key: str = ""
    default_knowledge: str = "syrian"
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "jazira_agri"
    db_user: str = "postgres"
    db_password: str = ""
    log_dir: str = "data/logs"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for name in ("password", "api_key", "secret_key", "database_url", "db_password"):
            value = data[name]
            data[name] = "***hidden***" if value else ""
        return data


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings(
        app_name=os.getenv("APP_NAME", "JaziraAgri-OS"),
        app_env=os.getenv("APP_ENV", "development"),
        username=os.getenv("JAZIRA_USERNAME", ""),
        password=os.getenv("JAZIRA_PASSWORD", ""),
        api_key=os.getenv("API_KEY", ""),
        secret_key=os.getenv("SECRET_KEY", ""),
        default_knowledge=os.getenv("DEFAULT_KNOWLEDGE", "syrian"),
        database_url=os.getenv("DATABASE_URL", ""),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "jazira_agri"),
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=os.getenv("DB_PASSWORD", ""),
        log_dir=os.getenv("LOG_DIR", "data/logs"),
    )
