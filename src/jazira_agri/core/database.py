from __future__ import annotations

import json
from typing import Any

from .configuration import get_settings


class DatabaseUnavailable(RuntimeError):
    pass


class PostgresRepository:
    """Optional PostgreSQL/PostGIS repository. It opens connections only on request."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.database_url or self.settings.db_password)

    def _connect(self):
        try:
            import psycopg2
        except ImportError as exc:
            raise DatabaseUnavailable(
                "PostgreSQL support is optional. Install it with: python -m pip install -e '.[postgres]'"
            ) from exc
        try:
            if self.settings.database_url:
                return psycopg2.connect(self.settings.database_url, connect_timeout=5)
            return psycopg2.connect(
                host=self.settings.db_host,
                port=self.settings.db_port,
                dbname=self.settings.db_name,
                user=self.settings.db_user,
                password=self.settings.db_password,
                connect_timeout=5,
            )
        except Exception as exc:
            raise DatabaseUnavailable("Could not connect to the configured PostgreSQL database") from exc

    def health(self) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)

    def list_farms(self) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id, name, region, owner, area_ha, notes, created_at FROM farms ORDER BY name")
            rows = cursor.fetchall()
        return [self._farm_dict(row) for row in rows]

    @staticmethod
    def _farm_dict(row: tuple[Any, ...]) -> dict[str, Any]:
        return {"id": str(row[0]), "name": row[1], "region": row[2], "owner": row[3] or "", "area_ha": float(row[4]), "notes": row[5] or "", "created_at": row[6].isoformat() if row[6] else ""}

    @staticmethod
    def _field_dict(row: tuple[Any, ...]) -> dict[str, Any]:
        return {"id": str(row[0]), "farm_id": str(row[1]), "name": row[2], "crop": row[3], "soil_type": row[4] or "", "irrigation": row[5] or "", "area_ha": float(row[6]), "latitude": float(row[7]) if row[7] is not None else None, "longitude": float(row[8]) if row[8] is not None else None, "status": row[9], "created_at": row[10].isoformat() if row[10] else ""}

    def create_farm(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = "INSERT INTO farms (name, region, owner, area_ha, notes) VALUES (%s, %s, %s, %s, %s) RETURNING id, name, region, owner, area_ha, notes, created_at"
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (payload["name"], payload["region"], payload.get("owner", ""), payload["area_ha"], payload.get("notes", "")))
            return self._farm_dict(cursor.fetchone())

    def list_fields(self, farm_id: str) -> list[dict[str, Any]]:
        query = """
            SELECT id, farm_id, name, crop, soil_type, irrigation, area_ha,
                   ST_Y(location::geometry), ST_X(location::geometry), status, created_at
            FROM fields WHERE farm_id = %s ORDER BY name
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (farm_id,))
            rows = cursor.fetchall()
        return [self._field_dict(row) for row in rows]

    def create_field(self, farm_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        query = """
            INSERT INTO fields (farm_id, name, crop, soil_type, irrigation, area_ha, location, status)
            VALUES (%s, %s, %s, %s, %s, %s,
                    CASE WHEN %s IS NULL OR %s IS NULL THEN NULL
                         ELSE ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geometry(Point,4326) END,
                    %s)
            RETURNING id, farm_id, name, crop, soil_type, irrigation, area_ha,
                      ST_Y(location::geometry), ST_X(location::geometry), status, created_at
        """
        lat, lon = payload.get("latitude"), payload.get("longitude")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (farm_id, payload["name"], payload["crop"], payload.get("soil_type"), payload.get("irrigation"), payload["area_ha"], lat, lon, lon, lat, payload.get("status", "active")))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(farm_id)
            return self._field_dict(row)

    def dashboard_counts(self) -> tuple[int, int]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT (SELECT COUNT(*) FROM farms), (SELECT COUNT(*) FROM fields)")
            return tuple(cursor.fetchone())  # type: ignore[return-value]

    def save_recommendation(self, record: dict[str, Any]) -> int:
        query = """
            INSERT INTO recommendations (username, crop, region, inputs, confidence, recommendation, result)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb)
            RETURNING id
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (record.get("username"), record["crop"], record["region"], json.dumps(record.get("inputs", {}), ensure_ascii=False), record.get("confidence", 0.0), json.dumps(record.get("recommendation", {}), ensure_ascii=False), json.dumps(record.get("result"), ensure_ascii=False) if record.get("result") is not None else None))
            return int(cursor.fetchone()[0])

    def recent_recommendations(self, limit: int = 20, *, farm_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT r.id, r.username, r.crop, r.region, r.inputs, r.confidence,
                   r.recommendation, r.result, r.created_at
            FROM recommendations r
            WHERE (%s IS NULL OR r.inputs->>'farm_id' = %s)
            ORDER BY r.created_at DESC LIMIT %s
        """
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, (farm_id, farm_id, limit))
            rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({"id": row[0], "username": row[1], "crop": row[2], "region": row[3], "inputs": row[4], "confidence": row[5], "recommendation": row[6], "result": row[7], "created_at": row[8].isoformat() if row[8] else ""})
        return result

    def farm_report(self, farm_id: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id, name, region, owner, area_ha, notes, created_at FROM farms WHERE id = %s", (farm_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            farm = self._farm_dict(row)
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(area_ha), 0) FROM fields WHERE farm_id = %s", (farm_id,))
            field_count, total_area = cursor.fetchone()
        return {"farm": farm, "field_count": int(field_count), "field_area_ha": float(total_area), "fields": self.list_fields(farm_id), "recommendations": self.recent_recommendations(50, farm_id=farm_id), "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
