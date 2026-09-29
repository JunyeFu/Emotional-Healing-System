from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class SessionStatus(str, Enum):
    CREATED = "CREATED"
    PREPARED = "PREPARED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class AssignmentBundle:
    allocation_index: int
    randomization_list_hash: str
    weather_sequence: tuple[str, ...]
    policy_decisions: tuple[Mapping[str, Any], ...] = ()
    permit_id: str | None = None
    reservation_id: str | None = None


@dataclass(frozen=True)
class OperatorRequest:
    request_id: str
    action: str
    reason_code: str | None = None


@dataclass(frozen=True)
class GateReceipt:
    gate: str
    evidence_id: str
    formal_capable: bool


@dataclass(frozen=True)
class AuditRecord:
    audit_seq: int
    event_id: str
    result: str
    reason_code: str | None
    observed_monotonic_ns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_seq": self.audit_seq,
            "event_id": self.event_id,
            "result": self.result,
            "reason_code": self.reason_code,
            "observed_monotonic_ns": self.observed_monotonic_ns,
        }


@dataclass(frozen=True)
class SessionEvent:
    event_schema_version: str
    session_id: str
    event_id: str
    event_seq: int
    event_type: str
    scheduled_monotonic_ns: int
    observed_monotonic_ns: int
    state_before: str
    state_after: str
    module_position: int | None
    module_id: str | None
    segment: str | None
    reason_code: str | None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_schema_version": self.event_schema_version,
            "session_id": self.session_id,
            "event_id": self.event_id,
            "event_seq": self.event_seq,
            "event_type": self.event_type,
            "scheduled_monotonic_ns": self.scheduled_monotonic_ns,
            "observed_monotonic_ns": self.observed_monotonic_ns,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "module_position": self.module_position,
            "module_id": self.module_id,
            "segment": self.segment,
            "reason_code": self.reason_code,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str | None
    schema_version: str
    status: SessionStatus
    module_id: str | None
    module_position: int | None
    segment: str | None
    segment_progress: float
    session_elapsed_ns: int
    paused_duration_ns: int
    last_control_seq: int
    runtime_mode: str | None
    cue_mode: str | None
    protocol_config_hash: str
    breath_protocol_config_version: str | None
    breath_protocol_config_hash: str | None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "session_id": self.session_id,
            "status": self.status.value,
            "module_id": self.module_id,
            "module_position": self.module_position,
            "segment": self.segment,
            "segment_progress": self.segment_progress,
            "session_elapsed_ns": self.session_elapsed_ns,
            "paused_duration_ns": self.paused_duration_ns,
            "last_control_seq": self.last_control_seq,
            "runtime_mode": self.runtime_mode,
            "cue_mode": self.cue_mode,
            "protocol_config_hash": self.protocol_config_hash,
        }
        if self.schema_version == "2.2":
            payload.update(
                schema_version=self.schema_version,
                breath_protocol_config_version=self.breath_protocol_config_version,
                breath_protocol_config_hash=self.breath_protocol_config_hash,
            )
        return payload


@dataclass(frozen=True)
class CoreUpdate:
    snapshot: SessionSnapshot
    control_events: tuple[Mapping[str, Any], ...] = ()
    session_events: tuple[SessionEvent, ...] = ()
    policy_decisions: tuple[Mapping[str, Any], ...] = ()
    audit_records: tuple[AuditRecord, ...] = ()
    gate_receipts: tuple[GateReceipt, ...] = ()


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    status: SessionStatus
    reason_code: str
    completed_modules: tuple[str, ...]
    session_elapsed_ns: int
    paused_duration_ns: int
    control_event_count: int
    session_event_count: int
    protocol_config_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "completed_modules": list(self.completed_modules),
            "session_elapsed_ns": self.session_elapsed_ns,
            "paused_duration_ns": self.paused_duration_ns,
            "control_event_count": self.control_event_count,
            "session_event_count": self.session_event_count,
            "protocol_config_hash": self.protocol_config_hash,
        }
