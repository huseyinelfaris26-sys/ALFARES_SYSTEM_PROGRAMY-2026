from __future__ import annotations

from typing import Any

from .configuration import get_settings


class DatabaseUnavailable(RuntimeError):
    pass


class PostgresRepository:
    """Small optional PostgreSQL adapter; connections are opened only on demand."""

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

    def save_recommendation(self, record: dict[str, Any]) -> int:
        query = """
            INSERT INTO recommendations
                (username, crop, region, inputs, confidence, recommendation, result)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb)
            RETURNING id
        """
        import json

        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    record.get("username"),
                    record["crop"],
                    record["region"],
                    json.dumps(record.get("inputs", {}), ensure_ascii=False),
                    record.get("confidence", 0.0),
                    json.dumps(record.get("recommendation", {}), ensure_ascii=False),
                    json.dumps(record.get("result"), ensure_ascii=False)
                    if record.get("result") is not None
                    else None,
                ),
            )
            return int(cursor.fetchone()[0])
