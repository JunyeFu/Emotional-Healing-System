from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .errors import RandomizationError
from .generator import verify_plan
from .models import (
    AllocationRecord,
    AllocationReceipt,
    AllocationRequest,
    BalanceAudit,
    GateEvidence,
    AuditIntegrity,
    RandomizationPlan,
)


_REQUIRED_GATES = ("eligibility", "device_readiness", "dedup_reservation")
_OUTCOMES = {"COMPLETE", "INCOMPLETE", "ABORTED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _opaque(prefix: str, *parts: object) -> str:
    payload = "\0".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:24]}"


def _event_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class RandomizationStore:
    def __init__(
        self,
        database_path: Path,
        *,
        evidence_verifier: object | None = None,
        formal_capable: bool = False,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.database_path = Path(database_path)
        self.evidence_verifier = evidence_verifier
        self.formal_capable = (
            formal_capable is True
            and getattr(evidence_verifier, "formal_capable", False) is True
        )
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _authorize(actual: str, required: str) -> None:
        if actual != required:
            raise RandomizationError("UNAUTHORIZED_ROLE")

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS randomization_lists (
                list_hash TEXT PRIMARY KEY,
                schema_version TEXT NOT NULL,
                randomization_version TEXT NOT NULL,
                stage TEXT NOT NULL,
                seed_commitment TEXT NOT NULL,
                imported_at_utc TEXT NOT NULL,
                UNIQUE(stage, randomization_version)
            );
            CREATE TABLE IF NOT EXISTS allocation_records (
                list_hash TEXT NOT NULL REFERENCES randomization_lists(list_hash),
                allocation_index INTEGER NOT NULL,
                stage TEXT NOT NULL,
                stratum TEXT NOT NULL,
                block_number INTEGER NOT NULL,
                arm TEXT NOT NULL,
                weather_sequence TEXT,
                arm_probability REAL NOT NULL,
                request_id TEXT,
                reservation_id TEXT UNIQUE,
                permit_id TEXT,
                assigned_at_utc TEXT,
                outcome TEXT,
                PRIMARY KEY(list_hash, allocation_index),
                UNIQUE(list_hash, request_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_allocation_request_id
                ON allocation_records(request_id) WHERE request_id IS NOT NULL;
            CREATE TABLE IF NOT EXISTS audit_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                result TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL DEFAULT '{}',
                previous_hash TEXT NOT NULL,
                current_hash TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS audit_anchor (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                event_count INTEGER NOT NULL,
                tail_hash TEXT NOT NULL
            );
            INSERT OR IGNORE INTO audit_anchor(id, event_count, tail_hash)
            VALUES (1, 0, 'GENESIS');
            """
        )
        return connection

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        event_type: str,
        object_id: str,
        result: str,
        reason_code: str,
        evidence_refs: dict[str, str] | None = None,
    ) -> str:
        previous = connection.execute(
            "SELECT current_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        anchor = connection.execute(
            "SELECT event_count, tail_hash FROM audit_anchor WHERE id = 1"
        ).fetchone()
        event_count = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        previous_hash = previous["current_hash"] if previous else "GENESIS"
        if anchor["event_count"] != event_count or anchor["tail_hash"] != previous_hash:
            raise RandomizationError("AUDIT_CHAIN_INVALID")
        payload: dict[str, object] = {
            "event_type": event_type,
            "object_id": object_id,
            "result": result,
            "reason_code": reason_code,
            "evidence_refs": evidence_refs or {},
            "previous_hash": previous_hash,
        }
        current_hash = _event_hash(payload)
        connection.execute(
            """
            INSERT INTO audit_events(
                event_type, object_id, result, reason_code, evidence_refs_json,
                previous_hash, current_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                object_id,
                result,
                reason_code,
                json.dumps(evidence_refs or {}, sort_keys=True, separators=(",", ":")),
                previous_hash,
                current_hash,
            ),
        )
        connection.execute(
            "UPDATE audit_anchor SET event_count = ?, tail_hash = ? WHERE id = 1",
            (event_count + 1, current_hash),
        )
        return current_hash

    @staticmethod
    def _audit_integrity(connection: sqlite3.Connection) -> AuditIntegrity:
        rows = connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
        anchor = connection.execute(
            "SELECT event_count, tail_hash FROM audit_anchor WHERE id = 1"
        ).fetchone()
        previous = "GENESIS"
        for row in rows:
            try:
                evidence_refs = json.loads(row["evidence_refs_json"])
            except (json.JSONDecodeError, TypeError):
                return AuditIntegrity(False, row["sequence"] - 1, "AUDIT_CHAIN_INVALID")
            payload: dict[str, object] = {
                "event_type": row["event_type"],
                "object_id": row["object_id"],
                "result": row["result"],
                "reason_code": row["reason_code"],
                "evidence_refs": evidence_refs,
                "previous_hash": previous,
            }
            if row["previous_hash"] != previous or row["current_hash"] != _event_hash(payload):
                return AuditIntegrity(False, row["sequence"] - 1, "AUDIT_CHAIN_INVALID")
            previous = row["current_hash"]
        if anchor["event_count"] != len(rows) or anchor["tail_hash"] != previous:
            return AuditIntegrity(False, len(rows), "AUDIT_ANCHOR_MISMATCH")
        return AuditIntegrity(True, len(rows), "AUDIT_CHAIN_VALID")

    @staticmethod
    def _verify_assignment_audit(connection: sqlite3.Connection) -> None:
        rows = connection.execute("SELECT * FROM allocation_records").fetchall()
        events = connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
        reveals: dict[str, list[sqlite3.Row]] = {}
        outcomes: dict[str, list[sqlite3.Row]] = {}
        for event in events:
            if event["event_type"] == "ASSIGNMENT_REVEALED":
                reveals.setdefault(event["object_id"], []).append(event)
            elif event["event_type"] == "OUTCOME_RECORDED":
                outcomes.setdefault(event["object_id"], []).append(event)

        expected_permits: set[str] = set()
        expected_outcomes: set[str] = set()
        for row in rows:
            mutable = (
                row["request_id"],
                row["reservation_id"],
                row["permit_id"],
                row["assigned_at_utc"],
            )
            if any(value is not None for value in mutable) and not all(
                value is not None for value in mutable
            ):
                raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")
            if row["request_id"] is None:
                if row["outcome"] is not None:
                    raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")
                continue
            permit = _opaque(
                "PERMIT",
                row["list_hash"],
                row["allocation_index"],
                row["request_id"],
                row["reservation_id"],
            )
            if row["permit_id"] != permit or len(reveals.get(permit, ())) != 1:
                raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")
            reveal = reveals[permit][0]
            try:
                refs = json.loads(reveal["evidence_refs_json"])
            except (json.JSONDecodeError, TypeError) as error:
                raise RandomizationError("ALLOCATION_AUDIT_MISMATCH") from error
            expected_refs = {*_REQUIRED_GATES, "allocation_binding"}
            expected_binding = _opaque(
                "BIND",
                row["list_hash"],
                row["allocation_index"],
                row["request_id"],
                row["reservation_id"],
                row["assigned_at_utc"],
            )
            if (
                set(refs) != expected_refs
                or refs.get("allocation_binding") != expected_binding
                or not all(isinstance(value, str) and value for value in refs.values())
            ):
                raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")
            expected_permits.add(permit)

            outcome_id = _opaque("ALLOC", row["list_hash"], row["allocation_index"])
            outcome_events = outcomes.get(outcome_id, ())
            if row["outcome"] is None:
                if outcome_events:
                    raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")
            elif len(outcome_events) != 1 or outcome_events[0]["reason_code"] != row["outcome"]:
                raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")
            else:
                expected_outcomes.add(outcome_id)
        if set(reveals) != expected_permits or set(outcomes) != expected_outcomes:
            raise RandomizationError("ALLOCATION_AUDIT_MISMATCH")

    @classmethod
    def _verify_runtime_integrity(cls, connection: sqlite3.Connection) -> None:
        report = cls._audit_integrity(connection)
        if not report.valid:
            raise RandomizationError(report.reason_code)
        cls._verify_assignment_audit(connection)

    @staticmethod
    def _verify_stored_list(connection: sqlite3.Connection, list_hash: str) -> None:
        metadata = connection.execute(
            "SELECT * FROM randomization_lists WHERE list_hash = ?", (list_hash,)
        ).fetchone()
        if metadata is None:
            raise RandomizationError("LIST_NOT_FOUND")
        rows = connection.execute(
            """
            SELECT * FROM allocation_records
            WHERE list_hash = ? ORDER BY allocation_index
            """,
            (list_hash,),
        ).fetchall()
        try:
            records = tuple(
                AllocationRecord(
                    allocation_index=row["allocation_index"],
                    stage=row["stage"],
                    stratum=row["stratum"],
                    block=row["block_number"],
                    arm=row["arm"],
                    weather_sequence=(
                        tuple(json.loads(row["weather_sequence"]))
                        if row["weather_sequence"] is not None
                        else None
                    ),
                    arm_behavior_probability=row["arm_probability"],
                )
                for row in rows
            )
        except (json.JSONDecodeError, TypeError) as error:
            raise RandomizationError("STORED_LIST_INVALID") from error
        verify_plan(
            RandomizationPlan(
                schema_version=metadata["schema_version"],
                randomization_version=metadata["randomization_version"],
                stage=metadata["stage"],
                block_size=48,
                seed_commitment=metadata["seed_commitment"],
                records=records,
                list_hash=metadata["list_hash"],
            )
        )

    def import_list(
        self, plan: RandomizationPlan, *, actor_role: str
    ) -> str:
        self._authorize(actor_role, "custodian")
        verify_plan(plan)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO randomization_lists(
                        list_hash, schema_version, randomization_version, stage,
                        seed_commitment, imported_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan.list_hash,
                        plan.schema_version,
                        plan.randomization_version,
                        plan.stage,
                        plan.seed_commitment,
                        _utc_now(),
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO allocation_records(
                        list_hash, allocation_index, stage, stratum, block_number,
                        arm, weather_sequence, arm_probability
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            plan.list_hash,
                            record.allocation_index,
                            record.stage,
                            record.stratum,
                            record.block,
                            record.arm,
                            json.dumps(record.weather_sequence)
                            if record.weather_sequence is not None
                            else None,
                            record.arm_behavior_probability,
                        )
                        for record in plan.records
                    ],
                )
                event_hash = self._append_event(
                    connection, "LIST_IMPORTED", plan.list_hash, "PASS", "LIST_SEALED"
                )
                connection.commit()
                return event_hash
        except sqlite3.IntegrityError as error:
            raise RandomizationError("LIST_ALREADY_IMPORTED") from error
        except (OSError, sqlite3.Error) as error:
            raise RandomizationError("STORE_UNAVAILABLE") from error

    @staticmethod
    def _validate_evidence(
        request: AllocationRequest, evidence: Iterable[GateEvidence]
    ) -> tuple[GateEvidence, ...]:
        evidence_tuple = tuple(evidence)
        by_gate = {item.gate: item for item in evidence_tuple}
        if len(by_gate) != len(evidence_tuple):
            raise RandomizationError("GATE_EVIDENCE_DUPLICATED")
        missing = set(_REQUIRED_GATES) - set(by_gate)
        if missing:
            raise RandomizationError("REQUIRED_GATE_MISSING")
        for gate in _REQUIRED_GATES:
            item = by_gate[gate]
            if item.passed is not True:
                raise RandomizationError("GATE_REJECTED", gate)
            if item.reservation_id != request.reservation_id:
                raise RandomizationError("GATE_RESERVATION_MISMATCH", gate)
            if not item.evidence_id:
                raise RandomizationError("GATE_EVIDENCE_MISSING", gate)
        return tuple(by_gate[gate] for gate in _REQUIRED_GATES)

    @staticmethod
    def _receipt(row: sqlite3.Row) -> AllocationReceipt:
        sequence = json.loads(row["weather_sequence"]) if row["weather_sequence"] else None
        return AllocationReceipt(
            allocation_index=row["allocation_index"],
            stage=row["stage"],
            stratum=row["stratum"],
            block=row["block_number"],
            arm=row["arm"],
            weather_sequence=tuple(sequence) if sequence is not None else None,
            arm_behavior_probability=row["arm_probability"],
            randomization_list_hash=row["list_hash"],
            randomization_version=row["randomization_version"],
            permit_id=row["permit_id"],
            reservation_id=row["reservation_id"],
            evidence_id=_opaque(
                "X01E", row["list_hash"], row["allocation_index"], row["request_id"]
            ),
        )

    def allocate_and_reveal(
        self,
        request: AllocationRequest,
        evidence: Iterable[GateEvidence],
        *,
        actor_role: str,
    ) -> AllocationReceipt:
        self._authorize(actor_role, "allocator")
        if (
            request.stage not in {"stage_1", "stage_3"}
            or not request.request_id
            or not request.stratum
            or not request.reservation_id
            or not request.expected_randomization_version
        ):
            raise RandomizationError("ALLOCATION_REQUEST_INVALID")
        evidence_tuple = self._validate_evidence(request, evidence)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._verify_runtime_integrity(connection)
                existing = connection.execute(
                    """
                    SELECT r.*, l.randomization_version
                    FROM allocation_records r
                    JOIN randomization_lists l USING(list_hash)
                    WHERE r.request_id = ?
                    """,
                    (request.request_id,),
                ).fetchone()
                if existing is not None:
                    self._verify_stored_list(connection, existing["list_hash"])
                    if (
                        existing["reservation_id"] != request.reservation_id
                        or existing["stage"] != request.stage
                        or existing["stratum"] != request.stratum
                        or existing["randomization_version"]
                        != request.expected_randomization_version
                    ):
                        raise RandomizationError("REQUEST_ID_CONFLICT")
                    self._append_event(
                        connection,
                        "ASSIGNMENT_REQUEST_REPEATED",
                        existing["permit_id"],
                        "PASS",
                        "IDEMPOTENT_REPLAY",
                    )
                    connection.commit()
                    return self._receipt(existing)
                reused = connection.execute(
                    "SELECT request_id FROM allocation_records WHERE reservation_id = ?",
                    (request.reservation_id,),
                ).fetchone()
                if reused is not None:
                    raise RandomizationError("RESERVATION_ALREADY_ALLOCATED")
                list_row = connection.execute(
                    """
                    SELECT * FROM randomization_lists
                    WHERE stage = ? AND randomization_version = ?
                    """,
                    (request.stage, request.expected_randomization_version),
                ).fetchone()
                if list_row is None:
                    raise RandomizationError("RANDOMIZATION_VERSION_UNAVAILABLE")
                self._verify_stored_list(connection, list_row["list_hash"])
                if self.evidence_verifier is None:
                    raise RandomizationError("GATE_VERIFIER_UNAVAILABLE")
                try:
                    self.evidence_verifier.verify_current(request, evidence_tuple)
                except AttributeError as error:
                    raise RandomizationError("GATE_VERIFIER_INVALID") from error
                row = connection.execute(
                    """
                    SELECT r.*, l.randomization_version
                    FROM allocation_records r
                    JOIN randomization_lists l USING(list_hash)
                    WHERE r.list_hash = ? AND r.stratum = ? AND r.request_id IS NULL
                    ORDER BY r.allocation_index
                    LIMIT 1
                    """,
                    (list_row["list_hash"], request.stratum),
                ).fetchone()
                if row is None:
                    raise RandomizationError("LIST_EXHAUSTED")
                assigned_at_utc = _utc_now()
                permit_id = _opaque(
                    "PERMIT",
                    row["list_hash"],
                    row["allocation_index"],
                    request.request_id,
                    request.reservation_id,
                )
                connection.execute(
                    """
                    UPDATE allocation_records
                    SET request_id = ?, reservation_id = ?, permit_id = ?, assigned_at_utc = ?
                    WHERE list_hash = ? AND allocation_index = ? AND request_id IS NULL
                    """,
                    (
                        request.request_id,
                        request.reservation_id,
                        permit_id,
                        assigned_at_utc,
                        row["list_hash"],
                        row["allocation_index"],
                    ),
                )
                self._append_event(
                    connection,
                    "ASSIGNMENT_REVEALED",
                    permit_id,
                    "PASS",
                    "ALL_GATES_PASS",
                    {
                        **{item.gate: item.evidence_id for item in evidence_tuple},
                        "allocation_binding": _opaque(
                            "BIND",
                            row["list_hash"],
                            row["allocation_index"],
                            request.request_id,
                            request.reservation_id,
                            assigned_at_utc,
                        ),
                    },
                )
                assigned = connection.execute(
                    """
                    SELECT r.*, l.randomization_version
                    FROM allocation_records r
                    JOIN randomization_lists l USING(list_hash)
                    WHERE r.list_hash = ? AND r.allocation_index = ?
                    """,
                    (row["list_hash"], row["allocation_index"]),
                ).fetchone()
                connection.commit()
                return self._receipt(assigned)
        except RandomizationError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise RandomizationError("STORE_UNAVAILABLE") from error

    def record_outcome(
        self,
        list_hash: str,
        allocation_index: int,
        outcome: str,
        *,
        actor_role: str,
    ) -> None:
        self._authorize(actor_role, "auditor")
        if outcome not in _OUTCOMES:
            raise RandomizationError("OUTCOME_INVALID")
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._verify_runtime_integrity(connection)
                self._verify_stored_list(connection, list_hash)
                current = connection.execute(
                    "SELECT outcome FROM allocation_records WHERE list_hash=? AND allocation_index=? "
                    "AND request_id IS NOT NULL",
                    (list_hash, allocation_index),
                ).fetchone()
                if current is None:
                    raise RandomizationError("ALLOCATION_NOT_FOUND")
                if current["outcome"] == outcome:
                    connection.rollback()
                    return
                if current["outcome"] is not None:
                    raise RandomizationError("OUTCOME_CONFLICT")
                updated = connection.execute(
                    """
                    UPDATE allocation_records SET outcome = ?
                    WHERE list_hash = ? AND allocation_index = ? AND request_id IS NOT NULL
                      AND outcome IS NULL
                    """,
                    (outcome, list_hash, allocation_index),
                ).rowcount
                if updated != 1:
                    raise RandomizationError("ALLOCATION_NOT_FOUND")
                self._append_event(
                    connection,
                    "OUTCOME_RECORDED",
                    _opaque("ALLOC", list_hash, allocation_index),
                    "PASS",
                    outcome,
                )
                connection.commit()
        except RandomizationError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise RandomizationError("STORE_UNAVAILABLE") from error

    def audit_balance(
        self, stage: str, stratum: str, *, actor_role: str
    ) -> BalanceAudit:
        self._authorize(actor_role, "auditor")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN")
            self._verify_runtime_integrity(connection)
            list_row = connection.execute(
                "SELECT list_hash FROM randomization_lists WHERE stage = ?",
                (stage,),
            ).fetchone()
            if list_row is None:
                raise RandomizationError("LIST_NOT_FOUND")
            self._verify_stored_list(connection, list_row["list_hash"])
            rows = connection.execute(
                """
                SELECT r.* FROM allocation_records r
                JOIN randomization_lists l USING(list_hash)
                WHERE l.stage = ? AND r.stratum = ? AND r.request_id IS NOT NULL
                ORDER BY r.allocation_index
                """,
                (stage, stratum),
            ).fetchall()
        arm_counts: dict[str, int] = {}
        for row in rows:
            arm_counts[row["arm"]] = arm_counts.get(row["arm"], 0) + 1
        assigned = len(rows)
        complete = sum(row["outcome"] == "COMPLETE" for row in rows)
        incomplete = sum(row["outcome"] in {"INCOMPLETE", "ABORTED"} for row in rows)
        balanced = assigned > 0 and assigned % 48 == 0 and len(set(arm_counts.values())) == 1
        return BalanceAudit(
            stage=stage,
            stratum=stratum,
            assigned_count=assigned,
            complete_count=complete,
            incomplete_count=incomplete,
            arm_counts=arm_counts,
            balanced_by_assignment=balanced,
            reason_code="BALANCED_BY_ASSIGNMENT" if balanced else "PARTIAL_BLOCK",
        )

    def verify_audit_chain(self, *, actor_role: str) -> AuditIntegrity:
        self._authorize(actor_role, "auditor")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN")
            report = self._audit_integrity(connection)
            if not report.valid:
                return report
            try:
                self._verify_assignment_audit(connection)
            except RandomizationError as error:
                return AuditIntegrity(False, report.checked_events, error.code)
            return report

    def validate_assignment(self, manifest: dict, assignment: object) -> str:
        list_hash = str(manifest["randomization_list_hash"])
        allocation_index = int(manifest["allocation_index"])
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN")
                self._verify_runtime_integrity(connection)
                self._verify_stored_list(connection, list_hash)
                row = connection.execute(
                    """
                    SELECT r.*, l.randomization_version
                    FROM allocation_records r
                    JOIN randomization_lists l USING(list_hash)
                    WHERE r.list_hash = ? AND r.allocation_index = ?
                      AND r.request_id IS NOT NULL
                    """,
                    (list_hash, allocation_index),
                ).fetchone()
        except RandomizationError as error:
            if error.code == "LIST_NOT_FOUND":
                raise RandomizationError("ASSIGNMENT_LIST_HASH_MISMATCH") from error
            raise
        except (OSError, sqlite3.Error) as error:
            raise RandomizationError("STORE_UNAVAILABLE") from error
        if row is None:
            raise RandomizationError("ASSIGNMENT_LIST_HASH_MISMATCH")
        expected = self._receipt(row)
        checks = {
            "ASSIGNMENT_STAGE_MISMATCH": manifest["study_stage"] == expected.stage,
            "ASSIGNMENT_STRATUM_MISMATCH": manifest["randomization_stratum"] == expected.stratum,
            "ASSIGNMENT_BLOCK_MISMATCH": int(manifest["randomization_block"]) == expected.block,
            "ASSIGNMENT_ARM_MISMATCH": manifest["assignment_arm"] == expected.arm,
            "ASSIGNMENT_CUE_MODE_MISMATCH": (
                expected.stage != "stage_1" or manifest["cue_mode"] == expected.arm
            ),
            "ASSIGNMENT_VERSION_MISMATCH": (
                manifest["randomization_version"] == expected.randomization_version
            ),
            "ASSIGNMENT_INDEX_MISMATCH": (
                getattr(assignment, "allocation_index") == expected.allocation_index
            ),
            "ASSIGNMENT_LIST_HASH_MISMATCH": (
                getattr(assignment, "randomization_list_hash")
                == expected.randomization_list_hash
            ),
            "ASSIGNMENT_PERMIT_MISMATCH": getattr(assignment, "permit_id") == expected.permit_id,
            "ASSIGNMENT_RESERVATION_MISMATCH": (
                getattr(assignment, "reservation_id") == expected.reservation_id
            ),
        }
        if expected.weather_sequence is not None:
            checks["ASSIGNMENT_SEQUENCE_MISMATCH"] = (
                tuple(manifest["weather_sequence"]) == expected.weather_sequence
                and tuple(getattr(assignment, "weather_sequence")) == expected.weather_sequence
            )
        for code, passed in checks.items():
            if not passed:
                raise RandomizationError(code)
        return expected.evidence_id
