from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PostgresDDL:
    """PostgreSQL/PostGIS schema template. Apply explicitly with psql or a migration tool."""

    @staticmethod
    def get_sql() -> str:
        return (Path(__file__).resolve().parents[3] / "data" / "sql" / "postgres_init.sql").read_text(
            encoding="utf-8"
        )


class RecommendationStore:
    """Offline/local JSONL recommendation ledger."""

    def __init__(self, base_dir: str = "data/logs/recommendations") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.base_dir / "history.jsonl"

    def append(self, payload: dict[str, Any]) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        record_path = self.base_dir / f"recommendation-{timestamp}.json"
        record_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.history_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return record_path

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        if not self.history_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.history_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    records.append(json.loads(line))
        return records[-limit:]
