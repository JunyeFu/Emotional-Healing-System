from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .errors import SessionCoreError


@dataclass(frozen=True)
class DurationRange:
    default_seconds: float
    minimum_seconds: float
    maximum_seconds: float


@dataclass(frozen=True)
class TransportConfig:
    bind_host: str
    tcp_control_port: int
    udp_td_port: int
    udp_unity_port: int
    telemetry_hz: float
    ack_timeout_ms: int
    max_send_attempts: int
    reconnect_grace_ms: int
    max_json_line_bytes: int
    max_scheduler_lag_ms: int


@dataclass(frozen=True)
class ProtocolConfig:
    protocol_config_version: str
    durations: dict[str, DurationRange]
    transport: TransportConfig
    config_hash: str


@dataclass(frozen=True)
class BreathStep:
    step_id: str
    phase: str
    duration_seconds: float


@dataclass(frozen=True)
class ModuleBreathProtocol:
    module_id: str
    steps: tuple[BreathStep, ...]


@dataclass(frozen=True)
class BreathProtocolConfig:
    breath_protocol_config_version: str
    modules: dict[str, ModuleBreathProtocol]
    config_hash: str
    source_payload: dict[str, Any]


_FROZEN_BREATH_PROTOCOL = {
    "storm": (
        ("inhale_1", "inhale", 3.0),
        ("hold_1", "hold", 3.0),
        ("exhale_1", "exhale", 3.0),
        ("hold_2", "hold", 3.0),
    ),
    "heat": (
        ("inhale_1", "inhale", 4.0),
        ("exhale_1", "exhale", 6.0),
    ),
    "snow": (
        ("inhale_1", "inhale", 5.0),
        ("exhale_1", "exhale", 5.0),
    ),
    "fade": (
        ("inhale_1", "inhale", 2.5),
        ("inhale_2", "inhale", 1.5),
        ("exhale_1", "exhale", 6.0),
    ),
}


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def load_protocol_config(path: Path | None = None) -> ProtocolConfig:
    config_path = path or Path(__file__).with_name("config") / "protocol_config_v1.1.json"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SessionCoreError("PROTOCOL_CONFIG_UNAVAILABLE", str(config_path)) from error

    expected_top = {"protocol_config_version", "module_durations", "transport"}
    if not isinstance(payload, dict) or set(payload) != expected_top:
        raise SessionCoreError("PROTOCOL_CONFIG_INVALID", "top-level fields")

    duration_names = {"demo", "closed_loop", "lock_transition"}
    raw_durations = payload.get("module_durations")
    if not isinstance(raw_durations, dict) or set(raw_durations) != duration_names:
        raise SessionCoreError("PROTOCOL_CONFIG_INVALID", "module_durations")

    durations: dict[str, DurationRange] = {}
    for name in sorted(duration_names):
        value = raw_durations[name]
        if not isinstance(value, dict) or set(value) != {
            "default_seconds", "minimum_seconds", "maximum_seconds"
        }:
            raise SessionCoreError("PROTOCOL_CONFIG_INVALID", f"module_durations.{name}")
        numbers = tuple(value[key] for key in (
            "default_seconds", "minimum_seconds", "maximum_seconds"
        ))
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in numbers):
            raise SessionCoreError("PROTOCOL_CONFIG_INVALID", f"module_durations.{name}")
        default, minimum, maximum = map(float, numbers)
        if not 0 < minimum <= default <= maximum:
            raise SessionCoreError("PROTOCOL_CONFIG_INVALID", f"module_durations.{name}")
        durations[name] = DurationRange(default, minimum, maximum)

    raw_transport = payload.get("transport")
    required_transport = {
        "bind_host", "tcp_control_port", "udp_td_port", "udp_unity_port",
        "telemetry_hz", "ack_timeout_ms", "max_send_attempts",
        "reconnect_grace_ms", "max_json_line_bytes", "max_scheduler_lag_ms",
    }
    if not isinstance(raw_transport, dict) or set(raw_transport) != required_transport:
        raise SessionCoreError("PROTOCOL_CONFIG_INVALID", "transport")
    if raw_transport["bind_host"] != "127.0.0.1":
        raise SessionCoreError("NON_LOOPBACK_BIND_FORBIDDEN", str(raw_transport["bind_host"]))

    transport = TransportConfig(**raw_transport)
    if transport.telemetry_hz != 20:
        raise SessionCoreError("PROTOCOL_CONFIG_INVALID", "telemetry_hz")
    if min(
        transport.tcp_control_port,
        transport.udp_td_port,
        transport.udp_unity_port,
        transport.ack_timeout_ms,
        transport.max_send_attempts,
        transport.reconnect_grace_ms,
        transport.max_json_line_bytes,
        transport.max_scheduler_lag_ms,
    ) <= 0:
        raise SessionCoreError("PROTOCOL_CONFIG_INVALID", "positive transport values")

    return ProtocolConfig(
        protocol_config_version=str(payload["protocol_config_version"]),
        durations=durations,
        transport=transport,
        config_hash=_canonical_hash(payload),
    )


def load_breath_protocol_config(path: Path | None = None) -> BreathProtocolConfig:
    config_path = (
        path
        or Path(__file__).with_name("config") / "breath_protocol_config_v2.2.json"
    )
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SessionCoreError(
            "BREATH_PROTOCOL_CONFIG_UNAVAILABLE", str(config_path)
        ) from error
    if not isinstance(payload, dict) or set(payload) != {
        "breath_protocol_config_version",
        "modules",
    }:
        raise SessionCoreError("BREATH_PROTOCOL_CONFIG_INVALID", "top-level fields")
    if payload["breath_protocol_config_version"] != "2.2":
        raise SessionCoreError("BREATH_PROTOCOL_CONFIG_INVALID", "version")
    raw_modules = payload["modules"]
    if not isinstance(raw_modules, dict) or set(raw_modules) != set(
        _FROZEN_BREATH_PROTOCOL
    ):
        raise SessionCoreError("BREATH_PROTOCOL_CONFIG_INVALID", "modules")

    modules: dict[str, ModuleBreathProtocol] = {}
    for module_id, expected in _FROZEN_BREATH_PROTOCOL.items():
        raw_module = raw_modules[module_id]
        if not isinstance(raw_module, dict) or set(raw_module) != {"steps"}:
            raise SessionCoreError(
                "BREATH_PROTOCOL_CONFIG_INVALID", f"modules.{module_id}"
            )
        raw_steps = raw_module["steps"]
        if not isinstance(raw_steps, list) or len(raw_steps) != len(expected):
            raise SessionCoreError(
                "BREATH_PROTOCOL_CONFIG_INVALID", f"modules.{module_id}.steps"
            )
        steps: list[BreathStep] = []
        for index, (raw_step, expected_step) in enumerate(zip(raw_steps, expected)):
            detail = f"modules.{module_id}.steps.{index}"
            if not isinstance(raw_step, dict) or set(raw_step) != {
                "step_id",
                "phase",
                "duration_seconds",
            }:
                raise SessionCoreError("BREATH_PROTOCOL_CONFIG_INVALID", detail)
            duration = raw_step["duration_seconds"]
            if (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not math.isfinite(duration)
                or duration <= 0
            ):
                raise SessionCoreError("BREATH_PROTOCOL_CONFIG_INVALID", detail)
            actual = (raw_step["step_id"], raw_step["phase"], float(duration))
            if actual != expected_step:
                raise SessionCoreError("BREATH_PROTOCOL_CONFIG_INVALID", detail)
            steps.append(BreathStep(*actual))
        modules[module_id] = ModuleBreathProtocol(module_id, tuple(steps))

    return BreathProtocolConfig(
        breath_protocol_config_version="2.2",
        modules=modules,
        config_hash=_canonical_hash(payload),
        source_payload=deepcopy(payload),
    )
