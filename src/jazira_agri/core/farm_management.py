from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FarmRepository:
    """Simple JSON-backed store for farms and fields used by the laptop app."""

    def __init__(self, root_dir: str = "data/farms") -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.farms_path = self.root_dir / "farms.json"
        self.fields_path = self.root_dir / "fields.json"
        self._ensure_seed_data()

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def _seed_farms(self) -> dict[str, Any]:
        return {
            "farm-1": {
                "id": "farm-1",
                "name": "حقل تل أبيض 01",
                "region": "tal_abyad",
                "owner": "المزارع أ.",
                "area_ha": 18.5,
                "notes": "تجربة مبكرة على القمح",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        }

    def _seed_fields(self) -> dict[str, Any]:
        return {
            "field-1": {
                "id": "field-1",
                "farm_id": "farm-1",
                "name": "قطعة 01",
                "crop": "wheat",
                "soil_type": "clay_loam",
                "irrigation": "irrigated",
                "area_ha": 6.5,
                "latitude": 36.7,
                "longitude": 38.2,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        }

    def _ensure_seed_data(self) -> None:
        farms = self._read_json(self.farms_path)
        if not farms:
            self._write_json(self.farms_path, self._seed_farms())
        fields = self._read_json(self.fields_path)
        if not fields:
            self._write_json(self.fields_path, self._seed_fields())

    def list_farms(self) -> list[dict[str, Any]]:
        data = self._read_json(self.farms_path)
        return [dict(value) for value in sorted(data.values(), key=lambda item: item.get("name", ""))]

    def create_farm(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read_json(self.farms_path)
        farm_id = payload.get("id") or f"farm-{len(data) + 1}"
        record = {
            "id": farm_id,
            "name": payload["name"],
            "region": payload.get("region", "tal_abyad"),
            "owner": payload.get("owner", ""),
            "area_ha": float(payload.get("area_ha", 0.0)),
            "notes": payload.get("notes", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data[farm_id] = record
        self._write_json(self.farms_path, data)
        return record

    def get_farm(self, farm_id: str) -> dict[str, Any] | None:
        return self._read_json(self.farms_path).get(farm_id)

    def list_fields(self, farm_id: str) -> list[dict[str, Any]]:
        data = self._read_json(self.fields_path)
        return [dict(value) for value in sorted(data.values(), key=lambda item: item.get("name", "")) if value.get("farm_id") == farm_id]

    def create_field(self, farm_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        farm = self.get_farm(farm_id)
        if farm is None:
            raise KeyError(farm_id)
        data = self._read_json(self.fields_path)
        field_id = payload.get("id") or f"field-{len(data) + 1}"
        record = {
            "id": field_id,
            "farm_id": farm_id,
            "name": payload["name"],
            "crop": payload.get("crop", "wheat"),
            "soil_type": payload.get("soil_type", "loam"),
            "irrigation": payload.get("irrigation", "rainfed"),
            "area_ha": float(payload.get("area_ha", 0.0)),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "status": payload.get("status", "active"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data[field_id] = record
        self._write_json(self.fields_path, data)
        return record

    def recent_activity(self, limit: int = 5) -> list[dict[str, Any]]:
        farm_rows = self.list_farms()
        field_rows = []
        for farm in farm_rows:
            field_rows.extend(self.list_fields(farm["id"]))
        merged = [
            {"type": "farm", "name": item["name"], "region": item.get("region", ""), "created_at": item.get("created_at", "")}
            for item in farm_rows
        ] + [
            {"type": "field", "name": item["name"], "region": item.get("farm_id", ""), "created_at": item.get("created_at", "")}
            for item in field_rows
        ]
        merged.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return merged[:limit]
