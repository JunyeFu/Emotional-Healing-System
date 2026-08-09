"""SRP runtime contract v2.1 validation and compatibility filtering.

This module owns message shape and fail-closed validation only. Session state,
network retries, persistence, and rendering remain downstream responsibilities.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
import math
import re
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "2.1"
UDP_TD_PORT = 5005
UDP_UNITY_PORT = 5006
TCP_CONTROL_PORT = 5010

MESSAGE_TYPES = {
    "session_manifest",
    "control_event",
    "ack",
    "telemetry_frame",
    "policy_decision",
    "render_receipt",
}

WEATHERS = {"storm", "heat", "snow", "fade"}
STUDY_STAGES = {"level_c", "stage_1", "stage_3"}
RUNTIME_MODES = {
    "dev_mock",
    "dev_replay",
    "formal_level_c",
    "formal_stage_1",
    "formal_stage_3",
}
CUE_MODES = {"scene_native", "abstract_pacer"}
SEGMENTS = {"demo", "closed_loop", "lock_transition"}
PHASES = {"inhale", "hold", "exhale", "recovery", "none"}
FALLBACK_STATES = {"GOOD", "DEGRADED", "UNUSABLE", "DISCONNECTED"}
DEVICE_STATES = {"CONNECTED", "DEGRADED", "UNUSABLE", "DISCONNECTED"}
CONTROL_EVENTS = {"prepare", "start", "pause", "abort", "segment", "module", "end"}
ACK_RESULTS = {"applied", "duplicate_ignored", "rejected", "failed"}
SOURCE_POLICIES = {"real", "replay", "mock"}
DEVICE_SOURCES = {
    "resp": {"plux_respiban", "mock", "none"},
    "ecg": {"polar_h10", "mock", "none"},
}
KNOWN_BUILD_PATTERN = re.compile(
    r"^(?!.*[\r\n])(?!unknown$|unset$|none$).+", re.IGNORECASE
)
RFC3339_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class ContractValidationError(ValueError):
    """Raised when an input cannot safely enter the v2.1 runtime."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _fail(code: str, detail: str) -> None:
    raise ContractValidationError(code, detail)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _require_keys(payload: Mapping[str, Any], keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        _fail("MISSING_FIELD", ",".join(missing))


def _require_type(payload: Mapping[str, Any], key: str, expected: type | tuple[type, ...]) -> None:
    if not isinstance(payload[key], expected):
        _fail("INVALID_TYPE", key)


def _require_integer(payload: Mapping[str, Any], key: str, minimum: int = 0) -> None:
    value = payload[key]
    if isinstance(value, bool):
        _fail("INVALID_INTEGER", key)
    if isinstance(value, int):
        if value < minimum:
            _fail("INVALID_INTEGER", key)
        return
    if not isinstance(value, float) or not math.isfinite(value) or not value.is_integer() or value < minimum:
        _fail("INVALID_INTEGER", key)


def _require_number(payload: Mapping[str, Any], key: str) -> None:
    if not _is_number(payload[key]):
        _fail("INVALID_NUMBER", key)


def _require_enum(payload: Mapping[str, Any], key: str, allowed: set[str]) -> None:
    if not isinstance(payload[key], str) or payload[key] not in allowed:
        _fail("INVALID_ENUM", key)


def _require_nonempty_string(payload: Mapping[str, Any], key: str) -> None:
    _require_type(payload, key, str)
    if not payload[key]:
        _fail("EMPTY_FIELD", key)


def _require_nullable_string(payload: Mapping[str, Any], key: str) -> None:
    if payload[key] is not None and not isinstance(payload[key], str):
        _fail("INVALID_TYPE", key)


def _reject_unknown_keys(payload: Mapping[str, Any], allowed: set[str], detail: str) -> None:
    unknown = set(payload) - allowed
    if unknown:
        _fail("UNKNOWN_FIELD", f"{detail}:{','.join(sorted(unknown))}")


def _require_datetime(payload: Mapping[str, Any], key: str) -> None:
    _require_nonempty_string(payload, key)
    if not RFC3339_UTC_PATTERN.fullmatch(payload[key]):
        _fail("INVALID_DATETIME", key)
    try:
        parsed = datetime.fromisoformat(payload[key].replace("Z", "+00:00"))
    except ValueError:
        _fail("INVALID_DATETIME", key)
    if parsed.tzinfo is None:
        _fail("INVALID_DATETIME", key)


def _validate_common(payload: Any, message_type: str) -> None:
    if not isinstance(payload, Mapping):
        _fail("INVALID_TYPE", "payload")
    _require_keys(payload, ("schema_version", "message_type"))
    if payload["schema_version"] != SCHEMA_VERSION:
        _fail("UNSUPPORTED_VERSION", str(payload["schema_version"]))
    if payload["message_type"] != message_type:
        _fail("MESSAGE_TYPE_MISMATCH", str(payload["message_type"]))


KNOWN_FIELDS: dict[str, tuple[str, ...]] = {
    "session_manifest": (
        "schema_version", "message_type", "research_id", "session_id", "study_stage",
        "runtime_mode", "cue_mode", "assignment_arm", "allocation_index",
        "randomization_stratum", "randomization_block", "randomization_list_hash",
        "weather_sequence", "module_durations", "protocol_config_version",
        "randomization_version", "strategy_version", "device_config", "unity_build_hash",
        "python_commit", "td_build_hash", "source_policy", "created_utc",
    ),
    "control_event": (
        "schema_version", "message_type", "session_id", "event_id", "control_seq",
        "event_type", "issued_monotonic_ns", "effective_monotonic_ns", "clock_domain_id",
        "payload",
    ),
    "ack": (
        "schema_version", "message_type", "session_id", "event_id", "received_monotonic_ns",
        "applied_monotonic_ns", "unity_frame", "result", "error_code",
    ),
    "telemetry_frame": (
        "schema_version", "message_type", "session_id", "frame_seq", "clock_domain_id",
        "source_monotonic_ns", "received_monotonic_ns", "sent_monotonic_ns",
        "clock_offset_ns", "clock_drift_ppm", "sync_uncertainty_ns", "module_id",
        "module_position", "segment", "target_phase", "target_progress", "actual_phase",
        "actual_progress", "actual_confidence", "recovery_value", "recovery_locked",
        "signal_quality", "fallback_state", "fallback_reason", "resp_device_state",
        "ecg_device_state", "cue_mode", "runtime_mode", "policy_decision_id",
    ),
    "policy_decision": (
        "schema_version", "message_type", "decision_id", "session_id", "stage", "position",
        "candidate_actions", "selected_action", "behavior_probability",
        "target_policy_probability", "state_snapshot_hash", "random_draw", "reason_code",
        "fallback_applied", "fallback_reason", "policy_version", "created_monotonic_ns",
    ),
    "render_receipt": (
        "schema_version", "message_type", "receipt_id", "session_id", "event_id", "frame_seq",
        "unity_frame", "rendered_monotonic_ns", "module_id", "segment", "result", "error_code",
    ),
}


def _validate_manifest(payload: Mapping[str, Any]) -> None:
    required = KNOWN_FIELDS["session_manifest"]
    _require_keys(payload, required)
    for key in ("research_id", "session_id", "assignment_arm", "randomization_stratum",
                "randomization_list_hash", "protocol_config_version", "randomization_version",
                "unity_build_hash", "python_commit"):
        _require_nonempty_string(payload, key)
    _require_datetime(payload, "created_utc")
    _require_enum(payload, "study_stage", STUDY_STAGES)
    _require_enum(payload, "runtime_mode", RUNTIME_MODES)
    _require_enum(payload, "cue_mode", CUE_MODES)
    _require_enum(payload, "source_policy", SOURCE_POLICIES)
    _require_nullable_string(payload, "strategy_version")
    _require_nullable_string(payload, "td_build_hash")
    _require_integer(payload, "allocation_index")
    _require_integer(payload, "randomization_block", minimum=1)
    _require_type(payload, "weather_sequence", list)
    if (
        len(payload["weather_sequence"]) != 4
        or any(not isinstance(item, str) for item in payload["weather_sequence"])
        or set(payload["weather_sequence"]) != WEATHERS
    ):
        _fail("INVALID_WEATHER_SEQUENCE", "must be one permutation of four weather modules")
    _require_type(payload, "module_durations", Mapping)
    _require_keys(payload["module_durations"], ("demo", "closed_loop", "lock_transition"))
    _reject_unknown_keys(
        payload["module_durations"], {"demo", "closed_loop", "lock_transition"},
        "module_durations",
    )
    for key in ("demo", "closed_loop", "lock_transition"):
        _require_number(payload["module_durations"], key)
        if payload["module_durations"][key] <= 0:
            _fail("INVALID_DURATION", key)
    _require_type(payload, "device_config", Mapping)
    _require_keys(payload["device_config"], ("resp", "ecg"))
    for device in ("resp", "ecg"):
        _require_type(payload["device_config"], device, Mapping)
        _require_keys(payload["device_config"][device], ("source",))
        _reject_unknown_keys(
            payload["device_config"][device], {"source", "serial"},
            f"device_config.{device}",
        )
        _require_enum(payload["device_config"][device], "source", DEVICE_SOURCES[device])
        if "serial" in payload["device_config"][device]:
            _require_nonempty_string(payload["device_config"][device], "serial")
    _reject_unknown_keys(payload["device_config"], {"resp", "ecg"}, "device_config")
    if payload["runtime_mode"] == "dev_mock" and payload["source_policy"] != "mock":
        _fail("MODE_SOURCE_POLICY_MISMATCH", "dev_mock requires mock")
    if payload["runtime_mode"] == "dev_replay":
        if payload["source_policy"] != "replay":
            _fail("MODE_SOURCE_POLICY_MISMATCH", "dev_replay requires replay")
        if any(payload["device_config"][device]["source"] == "mock" for device in ("resp", "ecg")):
            _fail("REPLAY_MOCK_FORBIDDEN", "device_config")
    if payload["runtime_mode"].startswith("formal_"):
        expected_mode = {
            "level_c": "formal_level_c",
            "stage_1": "formal_stage_1",
            "stage_3": "formal_stage_3",
        }[payload["study_stage"]]
        if payload["runtime_mode"] != expected_mode:
            _fail("STAGE_MODE_MISMATCH", f"{payload['study_stage']}:{payload['runtime_mode']}")
        if payload["source_policy"] != "real":
            _fail("FORMAL_MOCK_FORBIDDEN", "source_policy/device_config")
        expected_sources = {"resp": "plux_respiban", "ecg": "polar_h10"}
        for device, expected in expected_sources.items():
            if payload["device_config"][device]["source"] != expected:
                _fail("FORMAL_SOURCE_REQUIRED", device)
        if not KNOWN_BUILD_PATTERN.fullmatch(payload["unity_build_hash"]):
            _fail("UNKNOWN_BUILD", "unity_build_hash")


def _validate_control(payload: Mapping[str, Any]) -> None:
    _require_keys(payload, KNOWN_FIELDS["control_event"])
    for key in ("session_id", "event_id", "clock_domain_id"):
        _require_nonempty_string(payload, key)
    for key in ("control_seq", "issued_monotonic_ns", "effective_monotonic_ns"):
        _require_integer(payload, key)
    _require_enum(payload, "event_type", CONTROL_EVENTS)
    _require_type(payload, "payload", Mapping)
    if payload["effective_monotonic_ns"] < payload["issued_monotonic_ns"]:
        _fail("INVALID_TIME_ORDER", "control effective before issued")
    if payload["event_type"] in {"segment", "module"} and not payload["payload"]:
        _fail("EMPTY_CONTROL_PAYLOAD", payload["event_type"])


def _validate_ack(payload: Mapping[str, Any]) -> None:
    _require_keys(payload, KNOWN_FIELDS["ack"])
    for key in ("session_id", "event_id"):
        _require_nonempty_string(payload, key)
    for key in ("received_monotonic_ns", "applied_monotonic_ns", "unity_frame"):
        _require_integer(payload, key)
    _require_enum(payload, "result", ACK_RESULTS)
    if payload["error_code"] is not None and not isinstance(payload["error_code"], str):
        _fail("INVALID_TYPE", "error_code")
    if payload["applied_monotonic_ns"] < payload["received_monotonic_ns"]:
        _fail("INVALID_TIME_ORDER", "ack applied before received")
    if payload["result"] == "applied" and payload["error_code"] is not None:
        _fail("INCONSISTENT_ACK", "applied requires null error_code")
    if payload["result"] != "applied" and not payload["error_code"]:
        _fail("INCONSISTENT_ACK", "non-applied requires error_code")


def _validate_telemetry(payload: Mapping[str, Any]) -> None:
    _require_keys(payload, KNOWN_FIELDS["telemetry_frame"])
    if "calm_index" in payload:
        _fail("RETIRED_FIELD", "calm_index")
    for key in ("session_id", "clock_domain_id", "module_id"):
        _require_nonempty_string(payload, key)
    for key in ("frame_seq", "source_monotonic_ns", "received_monotonic_ns",
                "sent_monotonic_ns", "module_position"):
        _require_integer(payload, key)
    for key in ("clock_offset_ns", "clock_drift_ppm", "sync_uncertainty_ns",
                "target_progress", "actual_progress", "actual_confidence", "recovery_value"):
        _require_number(payload, key)
    if payload["sync_uncertainty_ns"] < 0:
        _fail("OUT_OF_RANGE", "sync_uncertainty_ns")
    for key in ("target_progress", "actual_progress", "actual_confidence", "recovery_value"):
        if not 0 <= payload[key] <= 1:
            _fail("OUT_OF_RANGE", key)
    _require_enum(payload, "segment", SEGMENTS)
    _require_enum(payload, "target_phase", PHASES)
    _require_enum(payload, "actual_phase", PHASES)
    _require_enum(payload, "fallback_state", FALLBACK_STATES)
    _require_enum(payload, "resp_device_state", DEVICE_STATES)
    _require_enum(payload, "ecg_device_state", DEVICE_STATES)
    _require_enum(payload, "cue_mode", CUE_MODES)
    _require_enum(payload, "runtime_mode", RUNTIME_MODES)
    _require_type(payload, "recovery_locked", bool)
    _require_type(payload, "signal_quality", Mapping)
    _require_nullable_string(payload, "fallback_reason")
    _require_nullable_string(payload, "policy_decision_id")
    if not (
        payload["source_monotonic_ns"]
        <= payload["received_monotonic_ns"]
        <= payload["sent_monotonic_ns"]
    ):
        _fail("INVALID_TIME_ORDER", "telemetry source/received/sent")
    if payload["fallback_state"] == "GOOD" and payload["fallback_reason"] is not None:
        _fail("INCONSISTENT_FALLBACK", "GOOD requires null fallback_reason")
    if payload["fallback_state"] != "GOOD" and not payload["fallback_reason"]:
        _fail("MISSING_FALLBACK_REASON", payload["fallback_state"])
def _validate_policy(payload: Mapping[str, Any]) -> None:
    _require_keys(payload, KNOWN_FIELDS["policy_decision"])
    for key in ("decision_id", "session_id", "state_snapshot_hash", "reason_code"):
        _require_nonempty_string(payload, key)
    _require_enum(payload, "stage", {"stage_1", "stage_3"})
    _require_integer(payload, "position")
    _require_type(payload, "candidate_actions", list)
    if (
        not payload["candidate_actions"]
        or any(not isinstance(item, str) or item not in WEATHERS for item in payload["candidate_actions"])
        or len(set(payload["candidate_actions"])) != len(payload["candidate_actions"])
    ):
        _fail("INVALID_CANDIDATE_ACTIONS", "must be non-empty and unique")
    _require_enum(payload, "selected_action", WEATHERS)
    if payload["selected_action"] not in payload["candidate_actions"]:
        _fail("ILLEGAL_SELECTED_ACTION", str(payload["selected_action"]))
    for key in ("behavior_probability", "random_draw"):
        _require_number(payload, key)
        if not 0 <= payload[key] <= 1:
            _fail("OUT_OF_RANGE", key)
    if payload["stage"] == "stage_1":
        expected_probability = 1 / len(payload["candidate_actions"])
        if payload["behavior_probability"] != expected_probability:
            _fail("INVALID_STAGE_1_PROBABILITY", str(payload["behavior_probability"]))
    target_probability = payload["target_policy_probability"]
    if target_probability is not None and (not _is_number(target_probability) or not 0 <= target_probability <= 1):
        _fail("OUT_OF_RANGE", "target_policy_probability")
    _require_type(payload, "fallback_applied", bool)
    _require_nullable_string(payload, "fallback_reason")
    _require_nullable_string(payload, "policy_version")
    _require_integer(payload, "created_monotonic_ns")
    if payload["fallback_applied"] and not payload["fallback_reason"]:
        _fail("MISSING_FALLBACK_REASON", "policy_decision")
    if not payload["fallback_applied"] and payload["fallback_reason"] is not None:
        _fail("INCONSISTENT_FALLBACK", "fallback_applied=false requires null fallback_reason")


def _validate_receipt(payload: Mapping[str, Any]) -> None:
    _require_keys(payload, KNOWN_FIELDS["render_receipt"])
    for key in ("receipt_id", "session_id", "event_id", "module_id"):
        _require_nonempty_string(payload, key)
    for key in ("frame_seq", "unity_frame", "rendered_monotonic_ns"):
        _require_integer(payload, key)
    _require_enum(payload, "segment", SEGMENTS)
    _require_enum(payload, "result", {"rendered", "skipped", "failed"})
    _require_nullable_string(payload, "error_code")


VALIDATORS = {
    "session_manifest": _validate_manifest,
    "control_event": _validate_control,
    "ack": _validate_ack,
    "telemetry_frame": _validate_telemetry,
    "policy_decision": _validate_policy,
    "render_receipt": _validate_receipt,
}


def validate_and_filter(message_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a v2.1 message and return only contract-owned fields.

    Unknown fields are intentionally ignored after validation so newer senders
    cannot mutate older consumers through undeclared data.
    """
    if not isinstance(message_type, str) or message_type not in MESSAGE_TYPES:
        _fail("UNKNOWN_MESSAGE_TYPE", str(message_type))
    _validate_common(payload, message_type)
    VALIDATORS[message_type](payload)
    return {key: deepcopy(payload[key]) for key in KNOWN_FIELDS[message_type] if key in payload}


@dataclass(frozen=True)
class ControlAuditRecord:
    """Auditable outcome emitted before a control event is applied or rejected."""

    event_id: str
    control_seq: int
    result: str
    error_code: str | None


@dataclass
class ControlEventLedger:
    """Fail closed on duplicate event IDs or non-increasing control sequences."""

    event_ids: set[str] = field(default_factory=set)
    last_control_seq: int = -1
    audit_log: list[ControlAuditRecord] = field(default_factory=list)

    def accept(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        event = validate_and_filter("control_event", payload)
        if event["event_id"] in self.event_ids:
            self.audit_log.append(ControlAuditRecord(
                event_id=event["event_id"], control_seq=int(event["control_seq"]),
                result="duplicate_ignored", error_code="DUPLICATE_CONTROL",
            ))
            _fail("DUPLICATE_CONTROL", event["event_id"])
        if event["control_seq"] <= self.last_control_seq:
            self.audit_log.append(ControlAuditRecord(
                event_id=event["event_id"], control_seq=int(event["control_seq"]),
                result="rejected", error_code="STALE_CONTROL_SEQUENCE",
            ))
            _fail("STALE_CONTROL_SEQUENCE", str(event["control_seq"]))
        self.audit_log.append(ControlAuditRecord(
            event_id=event["event_id"], control_seq=int(event["control_seq"]),
            result="applied", error_code=None,
        ))
        self.event_ids.add(event["event_id"])
        self.last_control_seq = int(event["control_seq"])
        return event
