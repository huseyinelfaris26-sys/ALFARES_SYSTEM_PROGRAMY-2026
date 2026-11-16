"""
Offline-first SQLite storage with automatic synchronisation and conflict handling.
تخزين محلي (SQLite) بنمط Offline-First مع مزامنة تلقائية ومعالجة تضارب البيانات.

English
-------
Sensor readings and farming decisions are always written to a local SQLite
database first, so the field device keeps working with no connectivity. When
the network returns, a background worker pushes pending records to the server
and pulls remote changes. Every record carries a revision counter (``rev``)
and the revision last known to be on the server (``base_rev``); a conflict is
detected whenever both sides changed the same record, and is resolved by a
per-table policy (server wins, client wins, last-write-wins, or manual).

العربية
-------
تُكتب قراءات الحساسات والقرارات الزراعية دائماً في قاعدة SQLite المحلية أولاً،
فيستمر الجهاز الحقلي بالعمل دون اتصال. عند عودة الشبكة يدفع عامل خلفي السجلات
المعلّقة إلى الخادم ويجلب تغييراته. لكل سجل رقم مراجعة (``rev``) وآخر مراجعة
معروفة على الخادم (``base_rev``)؛ يُكتشف التضارب عندما يُعدَّل السجل نفسه على
الطرفين، ويُحل بسياسة لكل جدول (الخادم يفوز، العميل يفوز، آخر كتابة تفوز، يدوي).

Server contract / عقد الخادم (HttpRemoteBackend)
------------------------------------------------
GET  {base}/health                      -> 2xx when reachable
POST {base}/sync/{table}/push           body {"records": [record, ...]}
     -> {"accepted": [{"id", "rev"}], "conflicts": [record], "rejected": [{"id", "reason"}]}
     The server accepts a record when its stored rev == record.base_rev (or the record is new,
     or it is an exact replay); otherwise it returns its own copy under "conflicts".
GET  {base}/sync/{table}/pull?cursor=&limit=
     -> {"records": [record], "next_cursor": str|null, "has_more": bool}

Requires Python 3.11+ (standard library only). / يتطلب Python 3.11+ (مكتبة قياسية فقط).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import math
import random
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Protocol, Self, runtime_checkable

__all__ = [
    "ConflictPolicy",
    "ConflictStrategy",
    "DecisionStatus",
    "HttpRemoteBackend",
    "InMemoryRemoteBackend",
    "OfflineFirstStore",
    "PullResponse",
    "PushResponse",
    "RemoteBackend",
    "RemoteProtocolError",
    "RemoteUnavailableError",
    "SensorReading",
    "SensorType",
    "StoreError",
    "SyncConflictPendingError",
    "SyncReport",
    "SyncStatus",
]

logger = logging.getLogger(__name__)

SCHEMA_VERSION: Final[int] = 1

#: Syncable tables and their data columns (whitelist; also protects SQL building).
#: الجداول القابلة للمزامنة وأعمدتها (قائمة بيضاء تحمي أيضاً من حقن SQL).
SYNC_TABLES: Final[dict[str, tuple[str, ...]]] = {
    "sensor_readings": ("field_id", "device_id", "sensor_type", "value", "unit", "recorded_at"),
    "irrigation_decisions": ("field_id", "crop", "growth_stage", "decided_at", "status", "payload"),
}

_META_COLUMNS: Final[tuple[str, ...]] = ("rev", "base_rev", "updated_at", "origin_node", "deleted", "checksum")

_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sensor_readings (
    id          TEXT PRIMARY KEY,
    field_id    TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    rev         INTEGER NOT NULL DEFAULT 1,
    base_rev    INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL,
    origin_node TEXT NOT NULL,
    deleted     INTEGER NOT NULL DEFAULT 0 CHECK (deleted IN (0, 1)),
    checksum    TEXT NOT NULL,
    sync_state  TEXT NOT NULL DEFAULT 'pending' CHECK (sync_state IN ('pending', 'synced', 'conflict')),
    synced_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_readings_lookup ON sensor_readings (field_id, sensor_type, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_state  ON sensor_readings (sync_state);
CREATE TABLE IF NOT EXISTS irrigation_decisions (
    id           TEXT PRIMARY KEY,
    field_id     TEXT NOT NULL,
    crop         TEXT NOT NULL,
    growth_stage TEXT NOT NULL,
    decided_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'proposed',
    payload      TEXT NOT NULL,
    rev          INTEGER NOT NULL DEFAULT 1,
    base_rev     INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT NOT NULL,
    origin_node  TEXT NOT NULL,
    deleted      INTEGER NOT NULL DEFAULT 0 CHECK (deleted IN (0, 1)),
    checksum     TEXT NOT NULL,
    sync_state   TEXT NOT NULL DEFAULT 'pending' CHECK (sync_state IN ('pending', 'synced', 'conflict')),
    synced_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_field ON irrigation_decisions (field_id, decided_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_state ON irrigation_decisions (sync_state);
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name  TEXT NOT NULL,
    record_id   TEXT NOT NULL,
    local_json  TEXT NOT NULL,
    remote_json TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    resolution  TEXT,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_conflicts_open ON sync_conflicts (resolution, table_name, record_id);
CREATE TABLE IF NOT EXISTS sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status      TEXT NOT NULL,
    pushed      INTEGER NOT NULL,
    pulled      INTEGER NOT NULL,
    conflicts   INTEGER NOT NULL,
    rejected    INTEGER NOT NULL,
    error       TEXT
);
"""


# --------------------------------------------------------------------------- #
# Errors / الأخطاء
# --------------------------------------------------------------------------- #
class StoreError(RuntimeError):
    """Base store error. / الخطأ الأساسي للمخزن."""


class SyncConflictPendingError(StoreError):
    """
    Record has an unresolved manual conflict and cannot be edited.
    السجل فيه تضارب يدوي غير محلول ولا يمكن تعديله.
    """


class RemoteUnavailableError(StoreError):
    """
    Server unreachable or temporarily failing (retry later).
    الخادم غير متاح أو يفشل مؤقتاً (أعد المحاولة لاحقاً).
    """


class RemoteProtocolError(StoreError):
    """
    Server returned an invalid or rejected response.
    ردّ الخادم غير صالح أو مرفوض.
    """


# --------------------------------------------------------------------------- #
# Enumerations and value objects / التعدادات والكائنات
# --------------------------------------------------------------------------- #
class SensorType(StrEnum):
    """Common sensor types. / أنواع الحساسات الشائعة."""

    SOIL_MOISTURE = "soil_moisture"
    SOIL_EC = "soil_ec"
    WATER_EC = "water_ec"
    AIR_TEMPERATURE = "air_temperature"
    AIR_HUMIDITY = "air_humidity"
    WIND_SPEED = "wind_speed"
    SOLAR_RADIATION = "solar_radiation"
    RAINFALL = "rainfall"
    WATER_FLOW = "water_flow"
    PH = "ph"


class DecisionStatus(StrEnum):
    """Lifecycle of a decision. / دورة حياة القرار."""

    PROPOSED = "proposed"  # مقترح
    APPROVED = "approved"  # معتمد
    EXECUTED = "executed"  # منفَّذ
    CANCELLED = "cancelled"  # ملغى


class ConflictStrategy(StrEnum):
    """
    Conflict resolution strategy. / استراتيجية حل التضارب.

    SERVER_WINS / CLIENT_WINS / LAST_WRITE_WINS (by updated_at; tie -> server) / MANUAL
    """

    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    LAST_WRITE_WINS = "last_write_wins"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class ConflictPolicy:
    """
    Per-table conflict policy. / سياسة التضارب لكل جدول.

    Sensor readings are immutable facts, so the server copy wins; decisions are edited
    by people on both sides, so last-write-wins is the default.
    قراءات الحساسات حقائق ثابتة فيفوز الخادم؛ القرارات يعدّلها أشخاص من الطرفين فالافتراضي آخر كتابة.
    """

    by_table: Mapping[str, ConflictStrategy] = field(default_factory=lambda: {
        "sensor_readings": ConflictStrategy.SERVER_WINS,
        "irrigation_decisions": ConflictStrategy.LAST_WRITE_WINS,
    })
    default: ConflictStrategy = ConflictStrategy.SERVER_WINS

    def for_table(self, table: str) -> ConflictStrategy:
        """Strategy for a table. / الاستراتيجية الخاصة بجدول."""
        return self.by_table.get(table, self.default)


@dataclass(frozen=True, slots=True)
class SensorReading:
    """
    A sensor reading to store. / قراءة حساس للتخزين.

    recorded_at : naive datetimes are treated as UTC (التوقيت الساذج يُعامل كـ UTC)
    id          : optional idempotency key; generated if omitted (مفتاح اختياري لمنع التكرار)
    """

    field_id: str
    device_id: str
    sensor_type: SensorType | str
    value: float
    unit: str
    recorded_at: datetime | None = None
    id: str | None = None


class SyncStatus(StrEnum):
    """Result of a sync attempt. / نتيجة محاولة المزامنة."""

    SUCCESS = "success"
    OFFLINE = "offline"
    BUSY = "busy"
    FAILED = "failed"


@dataclass(slots=True)
class SyncReport:
    """
    Outcome of one synchronisation run. / نتيجة دورة مزامنة واحدة.
    """

    status: SyncStatus = SyncStatus.SUCCESS
    started_at: str = ""
    finished_at: str = ""
    pushed: int = 0
    pulled: int = 0
    conflicts_detected: int = 0
    conflicts_auto_resolved: int = 0
    conflicts_pending_manual: int = 0
    rejected: int = 0
    rebased: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        """Duration in seconds. / المدة بالثواني."""
        if not self.started_at or not self.finished_at:
            return 0.0
        return (_parse_ts(self.finished_at) - _parse_ts(self.started_at)).total_seconds()


@dataclass(frozen=True, slots=True)
class PushResponse:
    """Server answer to a push. / ردّ الخادم على الدفع."""

    accepted: Mapping[str, int]
    conflicts: Sequence[Mapping[str, Any]] = ()
    rejected: Sequence[Mapping[str, str]] = ()


@dataclass(frozen=True, slots=True)
class PullResponse:
    """Server answer to a pull page. / ردّ الخادم على صفحة جلب."""

    records: Sequence[Mapping[str, Any]]
    next_cursor: str | None
    has_more: bool = False


@runtime_checkable
class RemoteBackend(Protocol):
    """
    Transport used for synchronisation. / وسيط النقل المستخدم في المزامنة.
    Implementations must raise RemoteUnavailableError for network problems
    and RemoteProtocolError for invalid responses.
    """

    def is_available(self) -> bool:
        """Cheap connectivity check. / فحص اتصال خفيف."""
        ...

    def push(self, table: str, records: Sequence[Mapping[str, Any]]) -> PushResponse:
        """Send local changes. / إرسال التغييرات المحلية."""
        ...

    def pull(self, table: str, cursor: str | None, limit: int) -> PullResponse:
        """Fetch remote changes after cursor. / جلب التغييرات بعد المؤشر."""
        ...


# --------------------------------------------------------------------------- #
# Helpers / دوال مساعدة
# --------------------------------------------------------------------------- #
def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    """UTC ISO-8601 with milliseconds. / صيغة ISO بتوقيت UTC بالمللي ثانية."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds")


def _parse_ts(value: str) -> datetime:
    """Parse an ISO timestamp; naive values are UTC; garbage becomes the epoch."""
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime.fromtimestamp(0, UTC)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _check_table(table: str) -> None:
    if table not in SYNC_TABLES:
        raise StoreError(f"Unknown table: {table!r}")


def _record_checksum(table: str, data: Mapping[str, Any], deleted: int | bool) -> str:
    """SHA-256 over the canonical data columns. / بصمة SHA-256 لأعمدة البيانات."""
    canonical = {column: data[column] for column in SYNC_TABLES[table]}
    canonical["deleted"] = int(bool(deleted))
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _dump_payload(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------- #
# Transports / وسائط النقل
# --------------------------------------------------------------------------- #
class HttpRemoteBackend:
    """
    JSON-over-HTTPS transport (standard library only).
    وسيط JSON عبر HTTPS (مكتبة قياسية فقط).

    HTTPS is mandatory unless ``allow_insecure_http`` is set (e.g. trusted LAN gateway).
    HTTPS إلزامي إلا إذا فُعّل ``allow_insecure_http`` (مثلاً بوابة محلية موثوقة).
    """

    def __init__(self, base_url: str, *, api_token: str | None = None, timeout_s: float = 15.0,
                 allow_insecure_http: bool = False, user_agent: str = "jazira-agri-os/1.0") -> None:
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("base_url must be an http(s) URL / عنوان الخادم غير صالح")
        if parsed.scheme == "http" and not allow_insecure_http:
            raise ValueError("HTTPS required; pass allow_insecure_http=True to override / HTTPS مطلوب")
        self._base = base_url.rstrip("/")
        self._token = api_token
        self._timeout = timeout_s
        self._ua = user_agent

    def _request(self, method: str, path: str, body: Mapping[str, Any] | None = None,
                 timeout: float | None = None) -> Any:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(f"{self._base}{path}", data=data, method=method)
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", self._ua)
        if data is not None:
            request.add_header("Content-Type", "application/json; charset=utf-8")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(request, timeout=timeout or self._timeout) as response:  # noqa: S310
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code >= 500 or exc.code in {408, 429}:
                raise RemoteUnavailableError(f"HTTP {exc.code} from server") from exc
            raise RemoteProtocolError(f"HTTP {exc.code} from server") from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            raise RemoteUnavailableError(f"Network error: {exc}") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RemoteProtocolError("Server returned invalid JSON") from exc

    def is_available(self) -> bool:
        """GET /health. / فحص /health."""
        try:
            self._request("GET", "/health", timeout=min(self._timeout, 5.0))
        except StoreError:
            return False
        return True

    def push(self, table: str, records: Sequence[Mapping[str, Any]]) -> PushResponse:
        """POST changed records. / إرسال السجلات المتغيرة."""
        _check_table(table)
        result = self._request("POST", f"/sync/{urllib.parse.quote(table)}/push", {"records": list(records)})
        try:
            accepted = {str(item["id"]): int(item["rev"]) for item in result.get("accepted", [])}
            return PushResponse(accepted=accepted, conflicts=list(result.get("conflicts", [])),
                                rejected=list(result.get("rejected", [])))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise RemoteProtocolError("Malformed push response") from exc

    def pull(self, table: str, cursor: str | None, limit: int) -> PullResponse:
        """GET remote changes. / جلب التغييرات البعيدة."""
        _check_table(table)
        query = {"limit": str(limit)}
        if cursor:
            query["cursor"] = cursor
        result = self._request("GET", f"/sync/{urllib.parse.quote(table)}/pull?{urllib.parse.urlencode(query)}")
        try:
            return PullResponse(records=list(result.get("records", [])),
                                next_cursor=result.get("next_cursor"),
                                has_more=bool(result.get("has_more", False)))
        except (TypeError, AttributeError) as exc:
            raise RemoteProtocolError("Malformed pull response") from exc


class InMemoryRemoteBackend:
    """
    Reference server implementing the contract in memory (tests, demos, simulation).
    خادم مرجعي في الذاكرة ينفذ العقد نفسه (للاختبار والمحاكاة).
    """

    def __init__(self) -> None:
        self.online: bool = True
        self._tables: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in SYNC_TABLES}
        self._seq = 0
        self._lock = threading.RLock()

    def _guard(self) -> None:
        if not self.online:
            raise RemoteUnavailableError("simulated outage")

    def is_available(self) -> bool:
        """Connectivity flag. / حالة الاتصال."""
        return self.online

    def push(self, table: str, records: Sequence[Mapping[str, Any]]) -> PushResponse:
        """Accept/conflict logic based on rev/base_rev. / منطق القبول والتضارب."""
        self._guard()
        _check_table(table)
        accepted: dict[str, int] = {}
        conflicts: list[dict[str, Any]] = []
        with self._lock:
            store = self._tables[table]
            for rec in records:
                rid = str(rec["id"])
                current = store.get(rid)
                replay = (current is not None and int(current["rev"]) == int(rec["rev"])
                          and current["checksum"] == rec["checksum"])
                if current is None or replay or int(current["rev"]) == int(rec["base_rev"]):
                    if not replay:
                        self._seq += 1
                        stored = {k: v for k, v in rec.items() if k != "base_rev"}
                        stored["_seq"] = self._seq
                        store[rid] = stored
                    accepted[rid] = int(rec["rev"])
                else:
                    conflicts.append({k: v for k, v in current.items() if k != "_seq"})
        return PushResponse(accepted=accepted, conflicts=conflicts)

    def pull(self, table: str, cursor: str | None, limit: int) -> PullResponse:
        """Return records newer than cursor. / إرجاع السجلات الأحدث من المؤشر."""
        self._guard()
        _check_table(table)
        after = int(cursor) if cursor else 0
        with self._lock:
            rows = sorted((r for r in self._tables[table].values() if r["_seq"] > after),
                          key=lambda r: r["_seq"])
        page = rows[:limit]
        records = [{k: v for k, v in r.items() if k != "_seq"} for r in page]
        next_cursor = str(page[-1]["_seq"]) if page else cursor
        return PullResponse(records=records, next_cursor=next_cursor, has_more=len(rows) > limit)

    def simulate_remote_edit(self, table: str, record_id: str, **changes: Any) -> None:
        """
        Edit a stored record as another node would. / تعديل سجل كما لو أنه من عقدة أخرى.
        """
        _check_table(table)
        with self._lock:
            rec = self._tables[table][record_id]
            rec.update(changes)
            rec["rev"] = int(rec["rev"]) + 1
            rec["updated_at"] = _iso(_utc_now())
            rec["origin_node"] = "server-simulated"
            rec["checksum"] = _record_checksum(table, rec, rec.get("deleted", 0))
            self._seq += 1
            rec["_seq"] = self._seq


# --------------------------------------------------------------------------- #
# Store / المخزن
# --------------------------------------------------------------------------- #
class OfflineFirstStore:
    """
    Offline-first SQLite store with background synchronisation.
    مخزن SQLite بنمط Offline-First مع مزامنة في الخلفية.

    Thread-safe: one connection guarded by a re-entrant lock; network I/O never holds it,
    so writes continue while a sync is in flight.
    آمن للخيوط: اتصال واحد محمي بقفل، ولا يُمسك القفل أثناء عمليات الشبكة.

    Example / مثال
    --------------
    >>> backend = HttpRemoteBackend("https://sync.example.org", api_token="...")
    >>> with OfflineFirstStore("data/jazira.db", backend=backend) as store:
    ...     store.save_sensor_reading("field-1", "probe-7", SensorType.SOIL_MOISTURE, 0.27, "m3/m3")
    ...     store.start_auto_sync(interval_s=30)
    """

    def __init__(self, db_path: str | Path, *, backend: RemoteBackend | None = None,
                 conflict_policy: ConflictPolicy | None = None, batch_size: int = 200) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1 / حجم الدفعة يجب أن يكون ≥ 1")
        self._path = str(db_path)
        if self._path != ":memory:":
            Path(self._path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._backend = backend
        self._policy = conflict_policy or ConflictPolicy()
        self._batch = batch_size
        self._lock = threading.RLock()
        self._sync_lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._worker: threading.Thread | None = None
        self._closed = False

        self._conn = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._configure()
        self._migrate()
        self.node_id: str = self._load_node_id()

    # -- lifecycle --------------------------------------------------------- #
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Stop the worker and close the database. / إيقاف العامل وإغلاق القاعدة."""
        if self._closed:
            return
        self.stop_auto_sync()
        with self._lock:
            self._closed = True
            self._conn.close()

    def _configure(self) -> None:
        with self._lock:
            if self._path != ":memory:":
                self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.execute("PRAGMA foreign_keys = ON")

    def _migrate(self) -> None:
        with self._lock:
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise StoreError(f"Database schema v{version} is newer than supported v{SCHEMA_VERSION}")
            if version < SCHEMA_VERSION:
                self._conn.executescript(_SCHEMA)
                self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @contextlib.contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        """Atomic write transaction (not re-entrant). / معاملة كتابة ذرية (غير متداخلة)."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")

    def _meta_get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def _meta_set_locked(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value))

    def _load_node_id(self) -> str:
        existing = self._meta_get("node_id")
        if existing:
            return existing
        node_id = uuid.uuid4().hex
        with self._tx():
            self._meta_set_locked("node_id", node_id)
        return node_id

    # ====================================================================== #
    # Local writes / الكتابة المحلية
    # ====================================================================== #
    def _insert_new_locked(self, table: str, record_id: str, data: dict[str, Any]) -> None:
        now = _iso(_utc_now())
        columns = ("id", *SYNC_TABLES[table], "rev", "base_rev", "updated_at", "origin_node",
                   "deleted", "checksum", "sync_state")
        values = (record_id, *(data[c] for c in SYNC_TABLES[table]), 1, 0, now, self.node_id, 0,
                  _record_checksum(table, data, 0), "pending")
        marks = ", ".join("?" for _ in columns)
        # INSERT OR IGNORE makes retries with the same id idempotent. / يجعل إعادة الإرسال بنفس المعرّف آمنة.
        self._conn.execute(f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) VALUES ({marks})", values)

    @staticmethod
    def _validate_reading(reading: SensorReading) -> dict[str, Any]:
        if not reading.field_id.strip() or not reading.device_id.strip():
            raise ValueError("field_id and device_id are required / معرّف الحقل والجهاز مطلوبان")
        sensor_type = str(reading.sensor_type).strip()
        if not sensor_type or not reading.unit.strip():
            raise ValueError("sensor_type and unit are required / نوع الحساس والوحدة مطلوبان")
        if not isinstance(reading.value, int | float) or not math.isfinite(reading.value):
            raise ValueError("value must be a finite number / القيمة يجب أن تكون رقماً محدداً")
        return {
            "field_id": reading.field_id.strip(),
            "device_id": reading.device_id.strip(),
            "sensor_type": sensor_type,
            "value": float(reading.value),
            "unit": reading.unit.strip(),
            "recorded_at": _iso(reading.recorded_at or _utc_now()),
        }

    def save_sensor_readings(self, readings: Sequence[SensorReading]) -> list[str]:
        """
        Store many readings atomically; returns their ids.
        تخزين عدة قراءات بشكل ذري وإرجاع معرّفاتها.
        """
        prepared = [(r.id or uuid.uuid4().hex, self._validate_reading(r)) for r in readings]
        if not prepared:
            return []
        with self._tx():
            for record_id, data in prepared:
                self._insert_new_locked("sensor_readings", record_id, data)
        return [record_id for record_id, _ in prepared]

    def save_sensor_reading(self, field_id: str, device_id: str, sensor_type: SensorType | str,
                            value: float, unit: str, recorded_at: datetime | None = None) -> str:
        """
        Store one reading; returns its id. / تخزين قراءة واحدة وإرجاع معرّفها.
        """
        return self.save_sensor_readings(
            [SensorReading(field_id, device_id, sensor_type, value, unit, recorded_at)])[0]

    def save_decision(self, field_id: str, crop: str, growth_stage: str, payload: Mapping[str, Any], *,
                      decided_at: datetime | None = None,
                      status: DecisionStatus = DecisionStatus.PROPOSED,
                      decision_id: str | None = None) -> str:
        """
        Store a farming decision (e.g. ``IrrigationRecommendation.to_dict()``).
        تخزين قرار زراعي (مثلاً ``IrrigationRecommendation.to_dict()``).
        """
        if not field_id.strip() or not crop.strip():
            raise ValueError("field_id and crop are required / معرّف الحقل والمحصول مطلوبان")
        record_id = decision_id or uuid.uuid4().hex
        data = {
            "field_id": field_id.strip(),
            "crop": crop.strip(),
            "growth_stage": str(growth_stage),
            "decided_at": _iso(decided_at or _utc_now()),
            "status": DecisionStatus(status).value,
            "payload": _dump_payload(payload),
        }
        with self._tx():
            self._insert_new_locked("irrigation_decisions", record_id, data)
        return record_id

    def _fetch_locked(self, table: str, record_id: str) -> sqlite3.Row | None:
        _check_table(table)
        return self._conn.execute(f"SELECT * FROM {table} WHERE id = ?", (record_id,)).fetchone()

    def _modify_locked(self, table: str, row: sqlite3.Row, changes: Mapping[str, Any], deleted: int) -> None:
        data = {c: row[c] for c in SYNC_TABLES[table]} | dict(changes)
        sets = ", ".join(f"{c} = ?" for c in (*changes, "rev", "updated_at", "origin_node", "deleted",
                                                "checksum", "sync_state"))
        values = (*changes.values(), int(row["rev"]) + 1, _iso(_utc_now()), self.node_id, deleted,
                  _record_checksum(table, data, deleted), "pending", row["id"])
        self._conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", values)

    def update_decision(self, decision_id: str, *, status: DecisionStatus | None = None,
                        payload: Mapping[str, Any] | None = None) -> None:
        """
        Edit a decision (status and/or payload). / تعديل قرار (الحالة و/أو المحتوى).
        Raises SyncConflictPendingError if a manual conflict is open.
        """
        changes: dict[str, Any] = {}
        if status is not None:
            changes["status"] = DecisionStatus(status).value
        if payload is not None:
            changes["payload"] = _dump_payload(payload)
        if not changes:
            return
        with self._tx():
            row = self._fetch_locked("irrigation_decisions", decision_id)
            if row is None or row["deleted"]:
                raise StoreError(f"Decision not found: {decision_id}")
            if row["sync_state"] == "conflict":
                raise SyncConflictPendingError(
                    f"Decision {decision_id} has an unresolved conflict / القرار فيه تضارب غير محلول")
            self._modify_locked("irrigation_decisions", row, changes, 0)

    def delete_decision(self, decision_id: str) -> None:
        """
        Soft-delete (tombstone synced to the server). / حذف ناعم يُزامَن مع الخادم.
        """
        with self._tx():
            row = self._fetch_locked("irrigation_decisions", decision_id)
            if row is None or row["deleted"]:
                raise StoreError(f"Decision not found: {decision_id}")
            if row["sync_state"] == "conflict":
                raise SyncConflictPendingError(
                    f"Decision {decision_id} has an unresolved conflict / القرار فيه تضارب غير محلول")
            self._modify_locked("irrigation_decisions", row, {}, 1)

    # ====================================================================== #
    # Local reads / القراءة المحلية
    # ====================================================================== #
    @staticmethod
    def _public(table: str, row: sqlite3.Row) -> dict[str, Any]:
        result = {key: row[key] for key in row.keys() if key != "payload"}
        if table == "irrigation_decisions":
            result["payload"] = json.loads(row["payload"])
        return result

    def get_recent_readings(self, field_id: str, sensor_type: SensorType | str | None = None, *,
                            limit: int = 100, since: datetime | None = None) -> list[dict[str, Any]]:
        """
        Latest readings, newest first. / أحدث القراءات، الأحدث أولاً.
        """
        sql = "SELECT * FROM sensor_readings WHERE field_id = ? AND deleted = 0"
        params: list[Any] = [field_id]
        if sensor_type is not None:
            sql += " AND sensor_type = ?"
            params.append(str(sensor_type))
        if since is not None:
            sql += " AND recorded_at >= ?"
            params.append(_iso(since))
        sql += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(max(1, limit))
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._public("sensor_readings", r) for r in rows]

    def get_latest_reading(self, field_id: str, sensor_type: SensorType | str) -> dict[str, Any] | None:
        """Most recent reading or None. / أحدث قراءة أو None."""
        rows = self.get_recent_readings(field_id, sensor_type, limit=1)
        return rows[0] if rows else None

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        """One decision or None. / قرار واحد أو None."""
        with self._lock:
            row = self._fetch_locked("irrigation_decisions", decision_id)
        if row is None or row["deleted"]:
            return None
        return self._public("irrigation_decisions", row)

    def list_decisions(self, field_id: str | None = None, status: DecisionStatus | None = None, *,
                       limit: int = 100) -> list[dict[str, Any]]:
        """Decisions, newest first. / القرارات، الأحدث أولاً."""
        sql = "SELECT * FROM irrigation_decisions WHERE deleted = 0"
        params: list[Any] = []
        if field_id is not None:
            sql += " AND field_id = ?"
            params.append(field_id)
        if status is not None:
            sql += " AND status = ?"
            params.append(DecisionStatus(status).value)
        sql += " ORDER BY decided_at DESC LIMIT ?"
        params.append(max(1, limit))
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._public("irrigation_decisions", r) for r in rows]

    def pending_counts(self) -> dict[str, dict[str, int]]:
        """
        Count of records by sync state per table. / عدد السجلات حسب حالة المزامنة لكل جدول.
        """
        result: dict[str, dict[str, int]] = {}
        with self._lock:
            for table in SYNC_TABLES:
                rows = self._conn.execute(
                    f"SELECT sync_state, COUNT(*) AS n FROM {table} GROUP BY sync_state").fetchall()
                counts = {"pending": 0, "synced": 0, "conflict": 0}
                counts.update({r["sync_state"]: int(r["n"]) for r in rows})
                result[table] = counts
        return result

    def purge_synced_readings(self, older_than_days: int = 30) -> int:
        """
        Delete synced readings older than N days (local only) to bound disk use.
        حذف القراءات المتزامنة الأقدم من N يوماً (محلياً فقط) للحد من استهلاك التخزين.
        """
        if older_than_days < 1:
            raise ValueError("older_than_days must be >= 1 / يجب أن تكون القيمة ≥ 1")
        cutoff = _iso(_utc_now() - timedelta(days=older_than_days))
        with self._tx() as conn:
            cursor = conn.execute(
                "DELETE FROM sensor_readings WHERE sync_state = 'synced' AND recorded_at < ?", (cutoff,))
            return cursor.rowcount

    # ====================================================================== #
    # Record <-> row conversion / تحويل السجلات
    # ====================================================================== #
    @staticmethod
    def _row_to_record(table: str, row: sqlite3.Row) -> dict[str, Any]:
        record: dict[str, Any] = {"id": row["id"]}
        for column in (*SYNC_TABLES[table], *_META_COLUMNS):
            record[column] = row[column]
        return record

    @staticmethod
    def _validate_remote(table: str, rec: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return a normalised remote record or None when invalid. / سجل بعيد مُطبَّع أو None."""
        try:
            clean: dict[str, Any] = {"id": str(rec["id"])}
            for column in SYNC_TABLES[table]:
                clean[column] = rec[column]
            if table == "sensor_readings":
                clean["value"] = float(clean["value"])
                if not math.isfinite(clean["value"]):
                    return None
            else:
                if not isinstance(clean["payload"], str):
                    clean["payload"] = _dump_payload(clean["payload"])
                json.loads(clean["payload"])
            clean["rev"] = int(rec["rev"])
            clean["updated_at"] = str(rec["updated_at"])
            clean["origin_node"] = str(rec.get("origin_node", "server"))
            clean["deleted"] = 1 if rec.get("deleted") else 0
            expected = _record_checksum(table, clean, clean["deleted"])
            if rec.get("checksum") not in (None, expected):
                logger.warning("Checksum mismatch for %s/%s; record rejected", table, clean["id"])
                return None
            clean["checksum"] = expected
            return clean
        except (KeyError, TypeError, ValueError):
            return None

    def _store_remote_locked(self, table: str, rec: Mapping[str, Any]) -> None:
        """Overwrite local row with the remote one, marked synced. / استبدال السجل المحلي بالبعيد كمتزامن."""
        columns = ("id", *SYNC_TABLES[table], "rev", "base_rev", "updated_at", "origin_node",
                   "deleted", "checksum", "sync_state", "synced_at")
        values = (rec["id"], *(rec[c] for c in SYNC_TABLES[table]), rec["rev"], rec["rev"], rec["updated_at"],
                  rec["origin_node"], rec["deleted"], rec["checksum"], "synced", _iso(_utc_now()))
        marks = ", ".join("?" for _ in columns)
        self._conn.execute(f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({marks})", values)

    # ====================================================================== #
    # Conflicts / التضارب
    # ====================================================================== #
    def _audit_conflict_locked(self, table: str, local: Mapping[str, Any], remote: Mapping[str, Any],
                               resolution: str | None) -> None:
        now = _iso(_utc_now())
        local_json = json.dumps(local, sort_keys=True, ensure_ascii=False)
        remote_json = json.dumps(remote, sort_keys=True, ensure_ascii=False)
        open_row = self._conn.execute(
            "SELECT id FROM sync_conflicts WHERE table_name = ? AND record_id = ? AND resolution IS NULL",
            (table, local["id"])).fetchone()
        if open_row is not None and resolution is None:
            self._conn.execute("UPDATE sync_conflicts SET local_json = ?, remote_json = ? WHERE id = ?",
                               (local_json, remote_json, open_row["id"]))
            return
        self._conn.execute(
            "INSERT INTO sync_conflicts (table_name, record_id, local_json, remote_json, detected_at, "
            "resolution, resolved_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (table, local["id"], local_json, remote_json, now, resolution, now if resolution else None))

    def _rebase_local_locked(self, table: str, row: sqlite3.Row, remote_rev: int) -> None:
        """Keep local content on top of remote revision; push again. / إبقاء المحتوى المحلي فوق مراجعة الخادم."""
        new_rev = max(int(row["rev"]), remote_rev) + 1
        self._conn.execute(
            f"UPDATE {table} SET rev = ?, base_rev = ?, sync_state = 'pending', updated_at = ? WHERE id = ?",
            (new_rev, remote_rev, _iso(_utc_now()), row["id"]))

    def _resolve_locked(self, table: str, row: sqlite3.Row, remote: dict[str, Any],
                        report: SyncReport) -> str:
        """
        Resolve one conflict inside an open transaction.
        Returns 'server', 'client' or 'manual'. / يحل تضارباً داخل معاملة مفتوحة.
        """
        strategy = self._policy.for_table(table)
        local_record = self._row_to_record(table, row)
        if strategy is ConflictStrategy.LAST_WRITE_WINS:
            local_newer = _parse_ts(local_record["updated_at"]) > _parse_ts(remote["updated_at"])
            strategy = ConflictStrategy.CLIENT_WINS if local_newer else ConflictStrategy.SERVER_WINS
        report.conflicts_detected += 1

        if strategy is ConflictStrategy.MANUAL:
            self._conn.execute(f"UPDATE {table} SET sync_state = 'conflict' WHERE id = ?", (row["id"],))
            self._audit_conflict_locked(table, local_record, remote, None)
            report.conflicts_pending_manual += 1
            return "manual"
        if strategy is ConflictStrategy.CLIENT_WINS:
            self._rebase_local_locked(table, row, int(remote["rev"]))
            self._audit_conflict_locked(table, local_record, remote, "client_wins")
            report.conflicts_auto_resolved += 1
            return "client"
        self._store_remote_locked(table, remote)
        self._audit_conflict_locked(table, local_record, remote, "server_wins")
        report.conflicts_auto_resolved += 1
        return "server"

    def list_conflicts(self, unresolved_only: bool = True) -> list[dict[str, Any]]:
        """
        Conflict audit trail. / سجل التضارب.
        """
        sql = "SELECT * FROM sync_conflicts"
        if unresolved_only:
            sql += " WHERE resolution IS NULL"
        sql += " ORDER BY id DESC"
        with self._lock:
            rows = self._conn.execute(sql).fetchall()
        result = []
        for row in rows:
            item = {k: row[k] for k in row.keys() if k not in {"local_json", "remote_json"}}
            item["local"] = json.loads(row["local_json"])
            item["remote"] = json.loads(row["remote_json"])
            result.append(item)
        return result

    def resolve_conflict(self, conflict_id: int, keep: str) -> None:
        """
        Manually resolve a conflict: keep='local' or keep='remote'.
        حل تضارب يدوياً: keep='local' أو keep='remote'.
        """
        if keep not in {"local", "remote"}:
            raise ValueError("keep must be 'local' or 'remote' / يجب أن تكون القيمة local أو remote")
        with self._tx() as conn:
            conflict = conn.execute("SELECT * FROM sync_conflicts WHERE id = ? AND resolution IS NULL",
                                    (conflict_id,)).fetchone()
            if conflict is None:
                raise StoreError(f"No open conflict with id {conflict_id}")
            table = conflict["table_name"]
            row = self._fetch_locked(table, conflict["record_id"])
            remote = self._validate_remote(table, json.loads(conflict["remote_json"]))
            if row is None or remote is None:
                raise StoreError("Conflict data is no longer valid / بيانات التضارب لم تعد صالحة")
            if keep == "remote":
                self._store_remote_locked(table, remote)
            else:
                self._rebase_local_locked(table, row, int(remote["rev"]))
            now = _iso(_utc_now())
            conn.execute("UPDATE sync_conflicts SET resolution = ?, resolved_at = ? WHERE id = ?",
                         (f"manual_{keep}", now, conflict_id))
        self.request_sync()

    # ====================================================================== #
    # Synchronisation / المزامنة
    # ====================================================================== #
    def sync_now(self) -> SyncReport:
        """
        Run one push+pull cycle. Never raises for network problems; see SyncReport.status.
        تشغيل دورة دفع وجلب واحدة؛ لا يرفع استثناء لمشاكل الشبكة (راجع status).
        """
        if self._backend is None:
            raise StoreError("No remote backend configured / لم يُضبط خادم للمزامنة")
        report = SyncReport(started_at=_iso(_utc_now()))
        if not self._sync_lock.acquire(blocking=False):
            report.status = SyncStatus.BUSY
            return report
        try:
            if not self._backend_available():
                report.status = SyncStatus.OFFLINE
                return report
            try:
                for table in SYNC_TABLES:
                    self._push_table(table, report)
                for table in SYNC_TABLES:
                    self._pull_table(table, report)
                if report.rebased:  # client-wins resolved while pulling: push them now
                    for table in SYNC_TABLES:
                        self._push_table(table, report)
                report.status = SyncStatus.SUCCESS
            except (StoreError, sqlite3.Error) as exc:
                report.status = SyncStatus.FAILED
                report.errors.append(str(exc))
                logger.warning("Sync failed: %s", exc)
            report.finished_at = _iso(_utc_now())
            self._log_sync(report)
            return report
        finally:
            if not report.finished_at:
                report.finished_at = _iso(_utc_now())
            self._sync_lock.release()

    def _backend_available(self) -> bool:
        try:
            return bool(self._backend and self._backend.is_available())
        except Exception:  # noqa: BLE001 - any transport failure means "offline"
            logger.debug("Connectivity check failed", exc_info=True)
            return False

    def _log_sync(self, report: SyncReport) -> None:
        try:
            with self._tx() as conn:
                conn.execute(
                    "INSERT INTO sync_log (started_at, finished_at, status, pushed, pulled, conflicts, "
                    "rejected, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (report.started_at, report.finished_at, report.status.value, report.pushed,
                     report.pulled, report.conflicts_detected, report.rejected,
                     "; ".join(report.errors) or None))
                conn.execute("DELETE FROM sync_log WHERE id NOT IN (SELECT id FROM sync_log ORDER BY id DESC LIMIT 500)")
        except sqlite3.Error:
            logger.exception("Could not write sync_log")

    # -- push -------------------------------------------------------------- #
    def _push_table(self, table: str, report: SyncReport) -> None:
        assert self._backend is not None
        with self._lock:
            ids = [r["id"] for r in self._conn.execute(
                f"SELECT id FROM {table} WHERE sync_state = 'pending' ORDER BY updated_at, id").fetchall()]
        for _ in range(3):  # initial pass + up to two client-wins retries
            retry_ids: list[str] = []
            for start in range(0, len(ids), self._batch):
                chunk = ids[start:start + self._batch]
                with self._lock:
                    marks = ", ".join("?" for _ in chunk)
                    rows = self._conn.execute(
                        f"SELECT * FROM {table} WHERE sync_state = 'pending' AND id IN ({marks})",
                        chunk).fetchall()
                if not rows:
                    continue
                records = [self._row_to_record(table, r) for r in rows]
                response = self._backend.push(table, records)  # network I/O without holding the lock
                retry_ids.extend(self._apply_push_response(table, response, report))
            if not retry_ids:
                return
            ids = retry_ids

    def _apply_push_response(self, table: str, response: PushResponse, report: SyncReport) -> list[str]:
        retries: list[str] = []
        with self._tx() as conn:
            now = _iso(_utc_now())
            for record_id, pushed_rev in response.accepted.items():
                cursor = conn.execute(
                    f"UPDATE {table} SET base_rev = ?, synced_at = ?, "
                    f"sync_state = CASE WHEN rev = ? THEN 'synced' ELSE 'pending' END "
                    f"WHERE id = ? AND sync_state = 'pending'",
                    (pushed_rev, now, pushed_rev, record_id))
                report.pushed += cursor.rowcount
            for item in response.rejected:
                report.rejected += 1
                logger.warning("Server rejected %s/%s: %s", table, item.get("id"), item.get("reason"))
            for raw in response.conflicts:
                remote = self._validate_remote(table, raw)
                if remote is None:
                    report.rejected += 1
                    continue
                row = self._fetch_locked(table, remote["id"])
                if row is None or row["sync_state"] != "pending":
                    continue
                if self._resolve_locked(table, row, remote, report) == "client":
                    retries.append(remote["id"])
        return retries

    # -- pull -------------------------------------------------------------- #
    def _pull_table(self, table: str, report: SyncReport) -> None:
        assert self._backend is not None
        cursor_key = f"pull_cursor:{table}"
        cursor = self._meta_get(cursor_key)
        while True:
            page = self._backend.pull(table, cursor, self._batch)
            for raw in page.records:
                remote = self._validate_remote(table, raw)
                if remote is None:
                    report.rejected += 1
                    continue
                with self._tx():
                    self._apply_remote_locked(table, remote, report)
            if page.next_cursor is not None and page.next_cursor != cursor:
                with self._tx():
                    self._meta_set_locked(cursor_key, page.next_cursor)
            if not page.has_more or page.next_cursor in (None, cursor):
                return
            cursor = page.next_cursor

    def _apply_remote_locked(self, table: str, remote: dict[str, Any], report: SyncReport) -> None:
        row = self._fetch_locked(table, remote["id"])
        if row is None:
            self._store_remote_locked(table, remote)
            report.pulled += 1
            return
        remote_rev = int(remote["rev"])
        state = row["sync_state"]
        if state == "synced":
            if remote_rev > int(row["rev"]):
                self._store_remote_locked(table, remote)
                report.pulled += 1
            return
        if state == "conflict":
            self._audit_conflict_locked(table, self._row_to_record(table, row), remote, None)
            return
        # state == 'pending': local edits not yet on the server
        if remote_rev <= int(row["base_rev"]):
            return  # remote is an old revision we already built upon
        if remote["checksum"] == row["checksum"] and remote["deleted"] == row["deleted"]:
            self._store_remote_locked(table, remote)  # both sides made the identical change
            return
        if self._resolve_locked(table, row, remote, report) == "client":
            report.rebased += 1
        else:
            report.pulled += 1

    # ====================================================================== #
    # Auto-sync worker / عامل المزامنة التلقائية
    # ====================================================================== #
    def request_sync(self) -> None:
        """
        Wake the worker for an immediate attempt. / إيقاظ العامل لمحاولة فورية.
        """
        self._wake.set()

    def start_auto_sync(self, interval_s: float = 30.0, *, max_backoff_s: float = 900.0,
                        on_complete: Callable[[SyncReport], None] | None = None) -> None:
        """
        Start the background worker: it polls connectivity every ``interval_s`` seconds, syncs when
        online, and backs off exponentially (with jitter) after failures.
        تشغيل عامل الخلفية: يفحص الاتصال كل ``interval_s`` ثانية ويزامن عند توفر الشبكة،
        ويتراجع أسّياً (مع عشوائية) بعد الإخفاق.
        """
        if self._backend is None:
            raise StoreError("No remote backend configured / لم يُضبط خادم للمزامنة")
        if interval_s <= 0 or max_backoff_s < interval_s:
            raise ValueError("Require interval_s > 0 and max_backoff_s >= interval_s")
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop.clear()
        self._wake.clear()
        self._worker = threading.Thread(
            target=self._auto_sync_loop, args=(interval_s, max_backoff_s, on_complete),
            name="jazira-offline-sync", daemon=True)
        self._worker.start()

    def stop_auto_sync(self, timeout_s: float | None = 5.0) -> None:
        """Stop the background worker. / إيقاف عامل الخلفية."""
        worker = self._worker
        if worker is None:
            return
        self._stop.set()
        self._wake.set()
        if worker is not threading.current_thread():
            worker.join(timeout_s)
        self._worker = None

    def _auto_sync_loop(self, interval: float, max_backoff: float,
                        on_complete: Callable[[SyncReport], None] | None) -> None:
        delay = 0.0  # first attempt immediately
        failures = 0
        while not self._stop.is_set():
            self._wake.wait(delay)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                report = self.sync_now()
            except Exception:  # noqa: BLE001 - the worker must survive unexpected errors
                logger.exception("Unexpected error in auto-sync")
                report = SyncReport(status=SyncStatus.FAILED, errors=["unexpected error"])
            if report.status is SyncStatus.FAILED:
                failures += 1
                delay = min(max_backoff, interval * (2 ** min(failures, 10))) * random.uniform(0.8, 1.2)
            else:
                failures = 0
                delay = interval
            if on_complete is not None and report.status in {SyncStatus.SUCCESS, SyncStatus.FAILED}:
                try:
                    on_complete(report)
                except Exception:  # noqa: BLE001
                    logger.exception("on_complete callback failed")
