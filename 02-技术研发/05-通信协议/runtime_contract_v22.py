"""SRP runtime contract v2.2 validation and compatibility filtering.

Version 2.2 preserves every v2.1 rule and adds explicit breath-protocol and
step-instance identity.  It is a separate module so the signed v2.1 contract
artifact remains byte-identical.
"""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
import math
import re
from typing import Any, Mapping


_v21 = import_module("05-通信协议.runtime_contract")

SCHEMA_VERSION = "2.2"
MESSAGE_TYPES = _v21.MESSAGE_TYPES
ContractValidationError = _v21.ContractValidationError

_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
STEP_PHASES: dict[str, dict[str, str]] = {
    "storm": {
        "inhale_1": "inhale",
        "hold_1": "hold",
        "exhale_1": "exhale",
        "hold_2": "hold",
    },
    "heat": {"inhale_1": "inhale", "exhale_1": "exhale"},
    "snow": {"inhale_1": "inhale", "exhale_1": "exhale"},
    "fade": {
        "inhale_1": "inhale",
        "inhale_2": "inhale",
        "exhale_1": "exhale",
    },
}

KNOWN_FIELDS: dict[str, tuple[str, ...]] = {
    **_v21.KNOWN_FIELDS,
    "session_manifest": (
        *_v21.KNOWN_FIELDS["session_manifest"],
        "breath_protocol_config_version",
        "breath_protocol_config_hash",
    ),
    "telemetry_frame": (
        *_v21.KNOWN_FIELDS["telemetry_frame"],
        "target_cycle_index",
        "target_step_id",
        "actual_cycle_index",
        "actual_step_id",
    ),
}


def _fail(code: str, detail: str) -> None:
    raise ContractValidationError(code, detail)


def _validate_common(message_type: str, payload: Mapping[str, Any]) -> None:
    if not isinstance(message_type, str) or message_type not in MESSAGE_TYPES:
        _fail("UNKNOWN_MESSAGE_TYPE", str(message_type))
    if not isinstance(payload, Mapping):
        _fail("INVALID_TYPE", "payload")
    missing = [key for key in ("schema_version", "message_type") if key not in payload]
    if missing:
        _fail("MISSING_FIELD", ",".join(missing))
    if payload["schema_version"] != SCHEMA_VERSION:
        _fail("UNSUPPORTED_VERSION", str(payload["schema_version"]))
    if payload["message_type"] != message_type:
        _fail("MESSAGE_TYPE_MISMATCH", str(payload["message_type"]))


def _validate_v21_fields(message_type: str, payload: Mapping[str, Any]) -> None:
    compatible = dict(payload)
    compatible["schema_version"] = _v21.SCHEMA_VERSION
    _v21.validate_and_filter(message_type, compatible)


def _validate_manifest(payload: Mapping[str, Any]) -> None:
    required = (
        "breath_protocol_config_version",
        "breath_protocol_config_hash",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        _fail("MISSING_FIELD", ",".join(missing))
    version = payload["breath_protocol_config_version"]
    if not isinstance(version, str):
        _fail("INVALID_TYPE", "breath_protocol_config_version")
    if not version:
        _fail("EMPTY_FIELD", "breath_protocol_config_version")
    config_hash = payload["breath_protocol_config_hash"]
    if not isinstance(config_hash, str):
        _fail("INVALID_TYPE", "breath_protocol_config_hash")
    if not _HASH_PATTERN.fullmatch(config_hash):
        _fail("INVALID_CONFIG_HASH", "breath_protocol_config_hash")


def _is_nonnegative_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    return (
        isinstance(value, float)
        and math.isfinite(value)
        and value.is_integer()
        and value >= 0
    )


def _validate_step_pair(payload: Mapping[str, Any], prefix: str) -> None:
    cycle_key = f"{prefix}_cycle_index"
    step_key = f"{prefix}_step_id"
    phase_key = f"{prefix}_phase"
    progress_key = f"{prefix}_progress"
    cycle = payload[cycle_key]
    step = payload[step_key]
    if (cycle is None) != (step is None):
        _fail("INCOMPLETE_STEP_IDENTITY", prefix)
    if cycle is None:
        if payload[phase_key] != "none" or payload[progress_key] != 0:
            _fail("EMPTY_STEP_STATE_MISMATCH", prefix)
        return
    if not _is_nonnegative_integer(cycle):
        _fail("INVALID_INTEGER", cycle_key)
    if not isinstance(step, str):
        _fail("INVALID_TYPE", step_key)
    module_id = payload["module_id"]
    steps = STEP_PHASES.get(module_id)
    if steps is None:
        _fail("INVALID_MODULE_ID", str(module_id))
    expected_phase = steps.get(step)
    if expected_phase is None:
        _fail("INVALID_STEP_ID", f"{module_id}:{step}")
    if payload[phase_key] != expected_phase:
        _fail("STEP_PHASE_MISMATCH", f"{prefix}:{step}")


def _validate_telemetry(payload: Mapping[str, Any]) -> None:
    required = (
        "target_cycle_index",
        "target_step_id",
        "actual_cycle_index",
        "actual_step_id",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        _fail("MISSING_FIELD", ",".join(missing))
    if payload["module_id"] not in STEP_PHASES:
        _fail("INVALID_MODULE_ID", str(payload["module_id"]))
    _validate_step_pair(payload, "target")
    _validate_step_pair(payload, "actual")


def validate_and_filter(message_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one v2.2 message and return only contract-owned fields."""
    _validate_common(message_type, payload)
    _validate_v21_fields(message_type, payload)
    if message_type == "session_manifest":
        _validate_manifest(payload)
    elif message_type == "telemetry_frame":
        _validate_telemetry(payload)
    return {
        key: deepcopy(payload[key])
        for key in KNOWN_FIELDS[message_type]
        if key in payload
    }
