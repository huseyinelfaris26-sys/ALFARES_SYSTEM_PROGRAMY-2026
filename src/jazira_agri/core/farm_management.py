from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FarmRepository:
    """Offline JSON-backed farm/field store. No synthetic farm records are created."""

    def __init__(self, root_dir: str = "data/farms") -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.farms_path = self.root_dir / "farms.json"
        self.fields_path = self.root_dir / "fields.json"
        self._ensure_files()

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid local data file: {path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Expected a JSON object in {path}")
        return value

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)

    def _ensure_files(self) -> None:
        for path in (self.farms_path, self.fields_path):
            if not path.exists():
                self._write_json(path, {})

    def list_farms(self) -> list[dict[str, Any]]:
        data = self._read_json(self.farms_path)
        return [dict(value) for value in sorted(data.values(), key=lambda item: item.get("name", ""))]

    def create_farm(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read_json(self.farms_path)
        farm_id = f"farm-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        record = {
            "id": farm_id,
            "name": payload["name"],
            "region": payload.get("region", "tal_abyad"),
            "owner": payload.get("owner", ""),
            "area_ha": float(payload["area_ha"]),
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
        if self.get_farm(farm_id) is None:
            raise KeyError(farm_id)
        data = self._read_json(self.fields_path)
        field_id = f"field-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        record = {
            "id": field_id,
            "farm_id": farm_id,
            "name": payload["name"],
            "crop": payload.get("crop", "wheat"),
            "soil_type": payload.get("soil_type", ""),
            "irrigation": payload.get("irrigation", ""),
            "area_ha": float(payload["area_ha"]),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "status": payload.get("status", "active"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data[field_id] = record
        self._write_json(self.fields_path, data)
        return record

    def recent_activity(self, limit: int = 5) -> list[dict[str, Any]]:
        farms = self.list_farms()
        fields = [field for farm in farms for field in self.list_fields(farm["id"])]
        result = [
            {"type": "farm", "name": farm["name"], "region": farm.get("region", ""), "created_at": farm.get("created_at", "")}
            for farm in farms
        ] + [
            {"type": "field", "name": field["name"], "region": field.get("farm_id", ""), "created_at": field.get("created_at", "")}
            for field in fields
        ]
        return sorted(result, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    def report(self, farm_id: str, recommendations: list[dict[str, Any]]) -> dict[str, Any] | None:
        farm = self.get_farm(farm_id)
        if farm is None:
            return None
        fields = self.list_fields(farm_id)
        return {
            "farm": farm,
            "field_count": len(fields),
            "field_area_ha": sum(float(item.get("area_ha", 0)) for item in fields),
            "fields": fields,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "caveat": "ملخص إداري للبيانات المسجلة، وليس تقييماً زراعياً أو قياساً ميدانياً.",
        }
