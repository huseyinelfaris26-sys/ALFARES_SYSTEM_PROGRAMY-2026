from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RecommendationRecord:
    crop: str
    region: str
    sowing_date: str | None
    soil_type: str | None
    rain_mm: float | None
    growth_stage: str | None
    confidence: float
    recommendation: dict[str, Any]
    result: dict[str, Any] | None = None
    created_at: str | None = None

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
            "created_at": self.created_at or datetime.now(timezone.utc).isoformat(),
        }


class RecommendationLog:
    """Persist recommendation records inside a local log directory."""

    def __init__(self, base_dir: str = "data/logs/recommendations") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: RecommendationRecord) -> Path:
        payload = record.to_dict()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_path = self.base_dir / f"{record.crop}-{timestamp}.json"
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def append(self, record: RecommendationRecord) -> dict[str, Any]:
        payload = record.to_dict()
        history_path = self.base_dir / "history.jsonl"
        with history_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        history_path = self.base_dir / "history.jsonl"
        if not history_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with history_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records[-limit:]
