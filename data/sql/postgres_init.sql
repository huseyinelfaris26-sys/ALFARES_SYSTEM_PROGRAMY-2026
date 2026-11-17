from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PostgresDDL:
    """SQL template for PostgreSQL/PostGIS setup. This file is used as a deployment template, not executed automatically."""

    @staticmethod
    def get_sql() -> str:
        return """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'operator',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    api_key TEXT,
    knowledge_base VARCHAR(32) NOT NULL DEFAULT 'syrian',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    region_id VARCHAR(64) NOT NULL UNIQUE,
    name_ar TEXT NOT NULL,
    name_en TEXT NOT NULL,
    governorate_ar TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    geometry GEOMETRY,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crop_knowledge (
    id SERIAL PRIMARY KEY,
    crop_id VARCHAR(64) NOT NULL,
    knowledge_base VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    crop VARCHAR(64) NOT NULL,
    region VARCHAR(64) NOT NULL,
    sowing_date TEXT,
    soil_type TEXT,
    rain_mm DOUBLE PRECISION,
    growth_stage TEXT,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    recommendation JSONB NOT NULL,
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    crop VARCHAR(64) NOT NULL,
    region VARCHAR(64) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


class RecommendationStore:
    """Simple file-backed recommendation ledger for offline/local environments."""

    def __init__(self, base_dir: str = "data/logs/recommendations") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.base_dir / "history.jsonl"

    def append(self, payload: dict[str, Any]) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        record_path = self.base_dir / f"recommendation-{timestamp}.json"
        record_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.history_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return record_path

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.history_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records[-limit:]
