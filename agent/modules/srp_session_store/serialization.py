from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Mapping


def json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if is_dataclass(value):
        if hasattr(value, "to_dict"):
            return json_value(value.to_dict())
        return json_value(asdict(value))
    return value


def serialize_core_output(value: Any) -> dict[str, Any]:
    if hasattr(value, "snapshot") and hasattr(value, "control_events"):
        return {
            "output_type": "CoreUpdate",
            "snapshot": json_value(value.snapshot),
            "control_events": json_value(value.control_events),
            "session_events": json_value(value.session_events),
            "policy_decisions": json_value(value.policy_decisions),
            "audit_records": json_value(value.audit_records),
            "gate_receipts": json_value(value.gate_receipts),
        }
    if hasattr(value, "to_dict"):
        return {"output_type": type(value).__name__, "value": json_value(value.to_dict())}
    return {"output_type": type(value).__name__, "value": json_value(value)}
