"""Compose the deterministic JaziraAgri engines into one field assessment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..advisor.diagnose import diagnose
from ..advisor.recommend import recommend
from .ai_provider import AgricultureAI
from .deficit_irrigation import (
    DailyWeather,
    DeficitIrrigationEngine,
    FieldConditions,
    IrrigationConfig,
)


def _without_local_photo_path(result: dict[str, Any]) -> dict[str, Any]:
    """Avoid disclosing local filesystem paths to an external AI provider."""
    safe = dict(result)
    safe.pop("stored_photo", None)
    return safe


class FieldAssistant:
    """Unified crop/seed, disease-image, and irrigation assessment facade.

    All deterministic engines continue to work offline. The AI provider is
    optional and receives only computed assessment values, never the image.
    """

    def __init__(
        self,
        *,
        ai_provider: AgricultureAI | None = None,
        irrigation_config: IrrigationConfig | None = None,
    ) -> None:
        self.ai_provider = ai_provider
        self.irrigation_engine = DeficitIrrigationEngine(irrigation_config)

    def assess(
        self,
        *,
        crop: str,
        farming: str,
        region: str = "tal_abyad",
        seasonal_rain_mm: float | None = None,
        irrigation_water_ec: float | None = None,
        symptoms: list[str] | None = None,
        photo: Path | None = None,
        weather: DailyWeather | None = None,
        field_conditions: FieldConditions | None = None,
        weather_observation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a unified assessment; weather/irrigation inputs are optional.

        ``weather`` and ``field_conditions`` must be supplied together. Weather
        forecasts can be obtained separately with ``WeatherForecast``; this
        method does not make network calls unless an AI provider is configured.
        """
        if (weather is None) != (field_conditions is None):
            raise ValueError("weather and field_conditions must be provided together")

        advice = recommend(
            crop=crop,
            farming=farming,
            region_name=region,
            rain_mm=seasonal_rain_mm,
            water_ec=irrigation_water_ec,
        )
        symptoms = symptoms or []
        diagnosis_result = diagnose(crop, symptoms, photo=photo) if (symptoms or photo is not None) else None
        irrigation_result = (
            self.irrigation_engine.recommend(weather, field_conditions).to_dict()
            if weather is not None and field_conditions is not None
            else None
        )

        assessment: dict[str, Any] = {
            "crop_advice": advice,
            "diagnosis": _without_local_photo_path(diagnosis_result) if diagnosis_result else None,
            "irrigation": irrigation_result,
            "weather": weather_observation,
            "ai_summary": None,
            "ai_error": None,
        }
        if self.ai_provider is not None:
            try:
                assessment["ai_summary"] = self.ai_provider.summarize({
                    "crop_advice": advice,
                    "diagnosis": assessment["diagnosis"],
                    "irrigation": irrigation_result,
                    "weather": weather_observation,
                })
            except Exception as exc:
                # Preserve the reliable deterministic results if the optional
                # network/model integration is unavailable.
                assessment["ai_error"] = f"AI summary unavailable: {type(exc).__name__}"
        return assessment


__all__ = ["FieldAssistant"]
