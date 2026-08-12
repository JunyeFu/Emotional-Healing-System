from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Callable
import uuid

from .errors import GovernanceError
from .phone import normalize_phone, phone_token


SCHEMA_VERSION = 1
TOKEN_VERSION = 1
_INITIALIZATION_LOCK = threading.Lock()
_RELEASE_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_ACTOR_ID = re.compile(r"^[a-z][a-z0-9-]{2,31}$")


class Stage(StrEnum):
    LEVEL_B = "level_b"
    LEVEL_C = "level_c"
    STAGE_1 = "stage_1"
    STAGE_3 = "stage_3"


class ReservationStatus(StrEnum):
    RESERVED = "RESERVED"
    RELEASED_BEFORE_EXPOSURE = "RELEASED_BEFORE_EXPOSURE"
    EXPOSED = "EXPOSED"
    COMPLETED = "COMPLETED"
    WITHDRAWN_AFTER_EXPOSURE = "WITHDRAWN_AFTER_EXPOSURE"


@dataclass(frozen=True)
class DedupDecision:
    allowed: bool
    reason_code: str
    reservation_id: str | None
    audit_event_id: str
    token_version: int


@dataclass(frozen=True)
class AuditReport:
    valid: bool
    reason_code: str
    checked_events: int
    checked_tokens: int = 0
    violation_count: int = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _opaque_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _audit_hash(record: dict) -> str:
    encoded = json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class DedupRegistry:
    def __init__(
        self,
        *,
        database_path: Path,
        key_provider: Callable[[], bytes],
        allowed_actors: set[str] | frozenset[str],
        timeout_seconds: float = 10.0,
    ) -> None:
        self.database_path = Path(database_path)
        self.key_provider = key_provider
        self.allowed_actors = frozenset(allowed_actors)
        self.timeout_seconds = timeout_seconds

    def _authorize(self, actor_id: str) -> None:
        if (
            not isinstance(actor_id, str)
            or not _ACTOR_ID.fullmatch(actor_id)
            or actor_id not in self.allowed_actors
        ):
            raise GovernanceError("UNAUTHORIZED")

    def _key(self) -> bytes:
        try:
            key = self.key_provider()
        except GovernanceError:
            raise
        except Exception as exc:
            raise GovernanceError("KEY_UNAVAILABLE") from exc
        if not isinstance(key, bytes) or len(key) != 32:
            raise GovernanceError("KEY_UNAVAILABLE")
        return key

    def _connect(self) -> sqlite3.Connection:
        connection: sqlite3.Connection | None = None
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(
                self.database_path,
                timeout=self.timeout_seconds,
                isolation_level=None,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
            with _INITIALIZATION_LOCK:
                connection.execute("PRAGMA journal_mode = WAL")
                self._initialize(connection)
            return connection
        except sqlite3.Error as exc:
            if connection is not None:
                connection.close()
            raise GovernanceError("REGISTRY_UNAVAILABLE") from exc

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id TEXT PRIMARY KEY,
                subject_token BLOB NOT NULL,
                token_version INTEGER NOT NULL,
                stage TEXT NOT NULL CHECK(stage IN ('level_b','level_c','stage_1','stage_3')),
                status TEXT NOT NULL CHECK(status IN (
                    'RESERVED','RELEASED_BEFORE_EXPOSURE','EXPOSED',
                    'COMPLETED','WITHDRAWN_AFTER_EXPOSURE'
                )),
                reserved_at_utc TEXT NOT NULL,
                updated_at_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_reservations_subject_token
                ON reservations(subject_token);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_one_blocking_record_per_token
                ON reservations(subject_token)
                WHERE status IN ('RESERVED','EXPOSED','COMPLETED','WITHDRAWN_AFTER_EXPOSURE');
            CREATE TABLE IF NOT EXISTS audit_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at_utc TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                result TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                current_hash TEXT NOT NULL UNIQUE
            );
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_metadata(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        row = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row["value"] != str(SCHEMA_VERSION):
            raise GovernanceError("SCHEMA_VERSION_UNSUPPORTED")

    @staticmethod
    def _append_audit(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        actor_id: str,
        object_type: str,
        object_id: str,
        result: str,
        reason_code: str,
    ) -> str:
        previous = connection.execute(
            "SELECT current_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        event_id = _opaque_id("AUD")
        record = {
            "event_id": event_id,
            "event_type": event_type,
            "actor_id": actor_id,
            "occurred_at_utc": _utc_now(),
            "object_type": object_type,
            "object_id": object_id,
            "result": result,
            "reason_code": reason_code,
            "previous_hash": previous["current_hash"] if previous else "GENESIS",
        }
        current_hash = _audit_hash(record)
        connection.execute(
            """
            INSERT INTO audit_events(
                event_id, event_type, actor_id, occurred_at_utc, object_type,
                object_id, result, reason_code, previous_hash, current_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*record.values(), current_hash),
        )
        return event_id

    def check_and_reserve(self, phone: str, stage: Stage | str, actor_id: str) -> DedupDecision:
        self._authorize(actor_id)
        key = self._key()
        canonical = normalize_phone(phone)
        token = phone_token(canonical, key)
        try:
            normalized_stage = Stage(stage)
        except (TypeError, ValueError) as exc:
            raise GovernanceError("INVALID_STAGE") from exc

        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                prior = connection.execute(
                    """
                    SELECT reservation_id, status
                    FROM reservations
                    WHERE subject_token = ?
                      AND status IN ('RESERVED','EXPOSED','COMPLETED','WITHDRAWN_AFTER_EXPOSURE')
                    LIMIT 1
                    """,
                    (token,),
                ).fetchone()
                if prior is not None:
                    reason = (
                        "ACTIVE_RESERVATION"
                        if prior["status"] == ReservationStatus.RESERVED
                        else "PRIOR_EXPOSURE"
                    )
                    event_id = self._append_audit(
                        connection,
                        event_type="CHECK_AND_RESERVE",
                        actor_id=actor_id,
                        object_type="SUBJECT_TOKEN",
                        object_id="OPAQUE_TOKEN",
                        result="DENIED",
                        reason_code=reason,
                    )
                    connection.commit()
                    return DedupDecision(False, reason, None, event_id, TOKEN_VERSION)

                reservation_id = _opaque_id("RSV")
                now = _utc_now()
                connection.execute(
                    """
                    INSERT INTO reservations(
                        reservation_id, subject_token, token_version, stage, status,
                        reserved_at_utc, updated_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reservation_id,
                        token,
                        TOKEN_VERSION,
                        normalized_stage.value,
                        ReservationStatus.RESERVED.value,
                        now,
                        now,
                    ),
                )
                event_id = self._append_audit(
                    connection,
                    event_type="CHECK_AND_RESERVE",
                    actor_id=actor_id,
                    object_type="RESERVATION",
                    object_id=reservation_id,
                    result="ALLOWED",
                    reason_code="NEW",
                )
                connection.commit()
                return DedupDecision(True, "NEW", reservation_id, event_id, TOKEN_VERSION)
            except sqlite3.IntegrityError:
                connection.rollback()
                raise GovernanceError("REGISTRY_UNAVAILABLE")
            except Exception:
                connection.rollback()
                raise

    def _transition(
        self,
        reservation_id: str,
        actor_id: str,
        *,
        from_statuses: tuple[ReservationStatus, ...],
        to_status: ReservationStatus,
        event_type: str,
        reason_code: str,
    ) -> None:
        self._authorize(actor_id)
        self._key()
        if not isinstance(reservation_id, str) or not reservation_id.startswith("RSV-"):
            raise GovernanceError("RESERVATION_NOT_FOUND")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM reservations WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise GovernanceError("RESERVATION_NOT_FOUND")
            if row["status"] not in {item.value for item in from_statuses}:
                connection.rollback()
                raise GovernanceError("INVALID_STATE_TRANSITION")
            connection.execute(
                "UPDATE reservations SET status = ?, updated_at_utc = ? WHERE reservation_id = ?",
                (to_status.value, _utc_now(), reservation_id),
            )
            self._append_audit(
                connection,
                event_type=event_type,
                actor_id=actor_id,
                object_type="RESERVATION",
                object_id=reservation_id,
                result="APPLIED",
                reason_code=reason_code,
            )
            connection.commit()

    def mark_exposed(self, reservation_id: str, actor_id: str) -> None:
        self._transition(
            reservation_id,
            actor_id,
            from_statuses=(ReservationStatus.RESERVED,),
            to_status=ReservationStatus.EXPOSED,
            event_type="MARK_EXPOSED",
            reason_code="EXPOSURE_RECORDED",
        )

    def release_before_exposure(self, reservation_id: str, reason: str, actor_id: str) -> None:
        if not isinstance(reason, str) or not _RELEASE_REASON.fullmatch(reason):
            raise GovernanceError("INVALID_RELEASE_REASON")
        self._transition(
            reservation_id,
            actor_id,
            from_statuses=(ReservationStatus.RESERVED,),
            to_status=ReservationStatus.RELEASED_BEFORE_EXPOSURE,
            event_type="RELEASE_BEFORE_EXPOSURE",
            reason_code=reason,
        )

    def mark_completed(self, reservation_id: str, actor_id: str) -> None:
        self._transition(
            reservation_id,
            actor_id,
            from_statuses=(ReservationStatus.EXPOSED,),
            to_status=ReservationStatus.COMPLETED,
            event_type="MARK_COMPLETED",
            reason_code="COMPLETED",
        )

    def mark_withdrawn_after_exposure(self, reservation_id: str, actor_id: str) -> None:
        self._transition(
            reservation_id,
            actor_id,
            from_statuses=(ReservationStatus.EXPOSED,),
            to_status=ReservationStatus.WITHDRAWN_AFTER_EXPOSURE,
            event_type="MARK_WITHDRAWN_AFTER_EXPOSURE",
            reason_code="WITHDRAWN_AFTER_EXPOSURE",
        )

    def verify_audit_chain(self) -> AuditReport:
        if not self.database_path.exists():
            raise GovernanceError("REGISTRY_UNAVAILABLE")
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
            previous_hash = "GENESIS"
            for row in rows:
                record = {
                    "event_id": row["event_id"],
                    "event_type": row["event_type"],
                    "actor_id": row["actor_id"],
                    "occurred_at_utc": row["occurred_at_utc"],
                    "object_type": row["object_type"],
                    "object_id": row["object_id"],
                    "result": row["result"],
                    "reason_code": row["reason_code"],
                    "previous_hash": row["previous_hash"],
                }
                if row["previous_hash"] != previous_hash or row["current_hash"] != _audit_hash(record):
                    return AuditReport(False, "AUDIT_CHAIN_INVALID", len(rows))
                previous_hash = row["current_hash"]
            token_count = connection.execute(
                "SELECT COUNT(DISTINCT subject_token) FROM reservations"
            ).fetchone()[0]
        return AuditReport(True, "OK", len(rows), token_count)

    def audit_tail_hash(self) -> str:
        if not self.database_path.exists():
            raise GovernanceError("REGISTRY_UNAVAILABLE")
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT current_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else "GENESIS"

    def record_operation(
        self,
        *,
        event_type: str,
        actor_id: str,
        object_type: str,
        object_id: str,
        result: str,
        reason_code: str,
    ) -> str:
        self._authorize(actor_id)
        self._key()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            event_id = self._append_audit(
                connection,
                event_type=event_type,
                actor_id=actor_id,
                object_type=object_type,
                object_id=object_id,
                result=result,
                reason_code=reason_code,
            )
            connection.commit()
        return event_id

    def audit_cross_stage(self) -> AuditReport:
        chain = self.verify_audit_chain()
        if not chain.valid:
            return chain
        with closing(sqlite3.connect(self.database_path)) as connection:
            violations = connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT subject_token
                    FROM reservations
                    WHERE status != 'RELEASED_BEFORE_EXPOSURE'
                    GROUP BY subject_token
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        return AuditReport(
            violations == 0,
            "OK" if violations == 0 else "CROSS_STAGE_DUPLICATE",
            chain.checked_events,
            chain.checked_tokens,
            violations,
        )


_default_registry: DedupRegistry | None = None


def configure_default_registry(registry: DedupRegistry) -> None:
    global _default_registry
    _default_registry = registry


def _registry_or_default(registry: DedupRegistry | None) -> DedupRegistry:
    if registry is None:
        if _default_registry is None:
            raise GovernanceError("REGISTRY_UNAVAILABLE")
        return _default_registry
    return registry


def check_and_reserve(
    phone: str,
    stage: Stage | str,
    actor_id: str,
    *,
    registry: DedupRegistry | None = None,
) -> DedupDecision:
    return _registry_or_default(registry).check_and_reserve(phone, stage, actor_id)


def mark_exposed(
    reservation_id: str,
    actor_id: str,
    *,
    registry: DedupRegistry | None = None,
) -> None:
    _registry_or_default(registry).mark_exposed(reservation_id, actor_id)


def release_before_exposure(
    reservation_id: str,
    reason: str,
    actor_id: str,
    *,
    registry: DedupRegistry | None = None,
) -> None:
    _registry_or_default(registry).release_before_exposure(reservation_id, reason, actor_id)


def audit_cross_stage(*, registry: DedupRegistry | None = None) -> AuditReport:
    return _registry_or_default(registry).audit_cross_stage()
