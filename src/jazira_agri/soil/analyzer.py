"""Soil analysis helpers for agronomic assessment."""

from __future__ import annotations

import math
from typing import Any


class SoilAnalyzer:
    """Evaluate basic soil indicators; outputs are advisory, not prescriptions."""

    def __init__(
        self,
        *,
        ph: float,
        salinity_ec: float,
        organic_matter: float | None = None,
        texture: str | None = None,
    ) -> None:
        self.ph = self._number(ph, "ph")
        if not 0 <= self.ph <= 14:
            raise ValueError("ph must be within 0..14")
        self.salinity_ec = self._number(salinity_ec, "salinity_ec")
        self.organic_matter = (
            self._number(organic_matter, "organic_matter") if organic_matter is not None else None
        )
        self.texture = texture.strip().lower() if isinstance(texture, str) and texture.strip() else None

    @staticmethod
    def _number(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"{name} must be numeric")
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"{name} must be finite and non-negative")
        return number

    @classmethod
    def from_profile(cls, profile: dict[str, Any]) -> "SoilAnalyzer":
        """Create an analyzer from a soil profile dictionary."""
        if not isinstance(profile, dict):
            raise TypeError("soil profile must be a dictionary")
        return cls(
            ph=profile.get("ph", 7.0),
            salinity_ec=profile.get("salinity_ec", 0.0),
            organic_matter=profile.get("organic_matter"),
            texture=profile.get("texture"),
        )

    def evaluate(self) -> dict[str, Any]:
        issues: list[str] = []
        recommendations: list[str] = []
        if self.ph < 5.5:
            issues.append("acidic_soil")
            recommendations.append("تحقق من تحليل التربة واستشر الإرشاد الزراعي قبل تعديل الحموضة.")
        elif self.ph > 7.5:
            issues.append("alkaline_soil")
            recommendations.append("تحقق من توفر العناصر الصغرى واستشر مختصاً قبل إضافة أي محسن.")

        if self.salinity_ec >= 4:
            issues.append("salinity_risk")
            recommendations.append("راقب الملوحة والصرف واختر المحصول وفق تحليل التربة ومياه الري.")
        elif self.salinity_ec >= 2:
            issues.append("moderate_salinity")
            recommendations.append("راقب الملوحة قبل زراعة المحاصيل الحساسة.")

        if self.organic_matter is not None and self.organic_matter < 1:
            issues.append("low_organic_matter")
            recommendations.append("يمكن تقييم إضافة مادة عضوية مناسبة بعد التحقق من التحليل المحلي.")
        if self.texture == "sandy":
            recommendations.append("التربة الرملية قد تحتاج ريّاً وتسميداً مجزأً؛ راجع ظروف الحقل.")
        elif self.texture in {"clay", "loam"}:
            recommendations.append("حافظ على الغطاء الأرضي وراقب الصرف وبنية التربة.")

        return {
            "ph": self.ph,
            "salinity_ec": self.salinity_ec,
            "organic_matter": self.organic_matter,
            "texture": self.texture,
            "status": "healthy" if not issues else "needs_attention",
            "issues": issues,
            "recommendations": recommendations,
            "advisory_only": True,
        }


__all__ = ["SoilAnalyzer"]
