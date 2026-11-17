from __future__ import annotations

from typing import Any

from .configuration import get_settings


def _default_dashboard(username: str) -> dict[str, Any]:
    return {
        "username": username,
        "knowledge_base": get_settings().default_knowledge,
        "deployment_mode": "local_laptop",
    }


class FarmDashboard:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get(self, username: str) -> dict[str, Any]:
        result = _default_dashboard(username)
        result["app_name"] = self.settings.app_name
        result["environment"] = self.settings.app_env
        return result
