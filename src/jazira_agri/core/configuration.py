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
    username: str = "admin"
    password: str = "change-me"
    api_key: str = ""
    default_knowledge: str = "syrian"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "jazira_agri"
    db_user: str = "postgres"
    db_password: str = "postgres"
    log_dir: str = "data/logs"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["password"] = "***hidden***" if self.password else ""
        data["api_key"] = "***hidden***" if self.api_key else ""
        return data


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings(
        app_name=os.getenv("APP_NAME", "JaziraAgri-OS"),
        app_env=os.getenv("APP_ENV", "development"),
        username=os.getenv("USERNAME", "admin"),
        password=os.getenv("PASSWORD", "change-me"),
        api_key=os.getenv("API_KEY", ""),
        default_knowledge=os.getenv("DEFAULT_KNOWLEDGE", "syrian"),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "jazira_agri"),
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=os.getenv("DB_PASSWORD", "postgres"),
        log_dir=os.getenv("LOG_DIR", "data/logs"),
    )
