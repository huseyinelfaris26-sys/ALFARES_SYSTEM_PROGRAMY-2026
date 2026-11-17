from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserAccount:
    username: str
    password_hash: str
    role: str = "operator"
    enabled: bool = True
    api_key: str = ""
    knowledge_base: str = "syrian"

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "role": self.role,
            "enabled": self.enabled,
            "api_key": self.api_key,
            "knowledge_base": self.knowledge_base,
        }


@dataclass
class RecommendationObservation:
    crop: str
    region: str
    sowing_date: str | None = None
    soil_type: str | None = None
    rain_mm: float | None = None
    growth_stage: str | None = None
    confidence: float = 0.0
    recommendation: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "crop": self.crop,
            "region": self.region,
            "sowing_date": self.sowing_date,
            "soil_type": self.soil_type,
            "rain_mm": self.rain_mm,
            "growth_stage": self.growth_stage,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "result": self.result,
        }
