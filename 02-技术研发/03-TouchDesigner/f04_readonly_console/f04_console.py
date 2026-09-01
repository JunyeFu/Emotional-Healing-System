"""Host-side authority for the F-04 static read-only console fixture.

This module is intentionally independent of TouchDesigner.  It validates the
formal TelemetryFrame through the existing F-01 reference validator and keeps
all display-only data outside the wire-format object.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping


FIXTURE_SCHEMA_VERSION = "f04-static-display-fixture-v1"
WEATHER_IDS = frozenset({"storm", "heat", "snow", "fade"})
QUALITY_STATES = frozenset({"GOOD", "DEGRADED", "UNUSABLE", "DISCONNECTED"})
BANNER = "READ ONLY / DEV-REPLAY / NOT LIVE"
SCENARIO_IDS = (
    "good_storm",
    "degraded_heat",
    "unusable_snow",
    "disconnected_fade",
    "out_of_order_storm",
)


def _load_contract_module():
    contract_path = (
        Path(__file__).resolve().parents[2]
        / "05-通信协议"
        / "runtime_contract.py"
    )
    spec = importlib.util.spec_from_file_location("srp_f01_runtime_contract", contract_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load F-01 contract validator: {contract_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CONTRACT = _load_contract_module()
FORMAL_TELEMETRY_FIELDS = frozenset(_CONTRACT.KNOWN_FIELDS["telemetry_frame"])


PAGE_DEFINITIONS = (
    {"id": "session_version", "title": "Session / Version", "banner": BANNER,
     "field_paths": ("telemetry.session_id", "telemetry.schema_version", "telemetry.runtime_mode", "telemetry.cue_mode")},
    {"id": "device_connection", "title": "Device Connection", "banner": BANNER,
     "field_paths": ("telemetry.resp_device_state", "telemetry.ecg_device_state")},
    {"id": "respiration_waveform", "title": "Raw / Filtered Respiration", "banner": BANNER,
     "field_paths": ("display_only.respiration.sample_rate_hz", "display_only.respiration.raw_25hz", "display_only.respiration.filtered_25hz")},
    {"id": "ecg_rr_quality", "title": "ECG / RR Quality", "banner": BANNER,
     "field_paths": ("telemetry.signal_quality.ecg", "display_only.rr_quality.rr_ms", "display_only.rr_quality.status")},
    {"id": "phase_comparison", "title": "Target / Actual Phase", "banner": BANNER,
     "field_paths": ("telemetry.target_phase", "telemetry.target_progress", "telemetry.actual_phase", "telemetry.actual_progress", "telemetry.actual_confidence")},
    {"id": "cycle_result", "title": "Cycle Result", "banner": BANNER,
     "field_paths": ("display_only.cycle_summary.cycle_id", "display_only.cycle_summary.duration_s", "display_only.cycle_summary.result")},
    {"id": "latency_clock", "title": "Latency / Clock", "banner": BANNER,
     "field_paths": ("telemetry.source_monotonic_ns", "telemetry.received_monotonic_ns", "telemetry.sent_monotonic_ns", "telemetry.clock_offset_ns", "telemetry.clock_drift_ppm", "telemetry.sync_uncertainty_ns")},
    {"id": "degradation", "title": "Degradation", "banner": BANNER,
     "field_paths": ("telemetry.fallback_state", "telemetry.fallback_reason", "telemetry.recovery_value", "telemetry.recovery_locked")},
    {"id": "log_write", "title": "Log Write", "banner": BANNER,
     "field_paths": ("display_only.log_status.write_state", "display_only.log_status.last_record_id", "display_only.log_status.notice")},
    {"id": "manual_actions", "title": "Manual Mark / Abort", "banner": BANNER,
     "field_paths": ("display_only.request_placeholders.manual_mark.status", "display_only.request_placeholders.abort.status")},
)


class FixtureValidationError(ValueError):
    """Fail-closed error for F-04 fixture or display-only data."""


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class ConsoleSnapshot:
    """Immutable display snapshot consumed by every F-04 page module."""

    meta: Mapping[str, Any]
    telemetry: Mapping[str, Any]
    display_only: Mapping[str, Any]

    def resolve(self, dotted_path: str) -> Any:
        root, separator, remainder = dotted_path.partition(".")
        if not separator or root not in {"meta", "telemetry", "display_only"}:
            raise KeyError(dotted_path)
        current: Any = getattr(self, root)
        for part in remainder.split("."):
            current = current[part]
        return current


class StaticFixtureAdapter:
    """F-04 adapter for deterministic local display scenarios."""

    def __init__(self, fixture_path: str | Path):
        fixture = load_and_validate_fixture(fixture_path)
        scenarios = {item["id"]: item for item in fixture["scenarios"]}
        if tuple(scenarios) != SCENARIO_IDS:
            _fail(f"scenario ids must be {SCENARIO_IDS}")
        self._fixture_id = fixture["fixture_schema_version"]
        self._scenarios = scenarios
        self._scenario_id = SCENARIO_IDS[0]
        self._page_id = PAGE_DEFINITIONS[0]["id"]

    @property
    def scenario_ids(self) -> tuple[str, ...]:
        return SCENARIO_IDS

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @scenario_id.setter
    def scenario_id(self, value: str) -> None:
        if value not in self._scenarios:
            raise ValueError(f"unknown scenario_id: {value}")
        self._scenario_id = value

    @property
    def page_id(self) -> str:
        return self._page_id

    @page_id.setter
    def page_id(self, value: str) -> None:
        if value not in {page["id"] for page in PAGE_DEFINITIONS}:
            raise ValueError(f"unknown page_id: {value}")
        self._page_id = value

    def read_snapshot(self) -> ConsoleSnapshot:
        scenario = self._scenarios[self._scenario_id]
        return ConsoleSnapshot(
            meta=_freeze({
                "fixture_id": self._fixture_id,
                "scenario_id": self._scenario_id,
                "page_id": self._page_id,
                "replay_state": "DEV-REPLAY",
            }),
            telemetry=_freeze(scenario["telemetry"]),
            display_only=_freeze(scenario["display_only"]),
        )


def _fail(message: str) -> None:
    raise FixtureValidationError(message)


def _assert_finite(value: Any, path: str = "fixture") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            _fail(f"non-finite number at {path}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_finite(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite(item, f"{path}[{index}]")
        return
    _fail(f"unsupported value at {path}: {type(value).__name__}")


def _validate_permissions(permissions: Any) -> None:
    if not isinstance(permissions, Mapping):
        _fail("permissions must be an object")
    expected_disabled = {
        "udp_5005": "T-01 NOT ACTIVE",
        "manual_mark": "T-02 NOT ACTIVE",
        "abort": "T-02 NOT ACTIVE",
    }
    for key, label in expected_disabled.items():
        entry = permissions.get(key)
        if not isinstance(entry, Mapping):
            _fail(f"missing permission {key}")
        active_key = "active" if key == "udp_5005" else "enabled"
        if entry.get(active_key) is not False or entry.get("label") != label:
            _fail(f"permission {key} must be disabled and labeled {label}")
    if permissions.get("network_outputs") != [] or permissions.get("spout_outputs") != []:
        _fail("F-04 cannot declare network or Spout outputs")


def _validate_display_only(display: Any, scenario_id: str) -> None:
    if not isinstance(display, Mapping):
        _fail(f"{scenario_id}: display_only must be an object")
    respiration = display.get("respiration")
    if not isinstance(respiration, Mapping) or respiration.get("sample_rate_hz") != 25:
        _fail(f"{scenario_id}: respiration must declare synthetic 25 Hz")
    for key in ("raw_25hz", "filtered_25hz"):
        values = respiration.get(key)
        if not isinstance(values, list) or len(values) != 25:
            _fail(f"{scenario_id}: {key} must contain exactly 25 samples")
    rr_quality = display.get("rr_quality")
    cycle = display.get("cycle_summary")
    log_status = display.get("log_status")
    placeholders = display.get("request_placeholders")
    if not all(isinstance(item, Mapping) for item in (rr_quality, cycle, log_status, placeholders)):
        _fail(f"{scenario_id}: incomplete display-only sections")
    for action in ("manual_mark", "abort"):
        entry = placeholders.get(action)
        if not isinstance(entry, Mapping) or entry.get("status") != "T-02 NOT ACTIVE" or entry.get("enabled") is not False:
            _fail(f"{scenario_id}: {action} must remain disabled")


def validate_fixture(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and filter an F-04 fixture without widening the v2.1 contract."""
    try:
        _assert_finite(payload)
        if payload.get("fixture_schema_version") != FIXTURE_SCHEMA_VERSION:
            _fail("unsupported fixture_schema_version")
        if payload.get("mode") != "DEV_REPLAY" or payload.get("banner") != BANNER:
            _fail("fixture must be visibly DEV_REPLAY and NOT LIVE")
        _validate_permissions(payload.get("permissions"))
        scenarios = payload.get("scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            _fail("scenarios must be a non-empty list")
        result = deepcopy(dict(payload))
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, Mapping):
                _fail(f"scenario[{index}] must be an object")
            scenario_id = scenario.get("id")
            if not isinstance(scenario_id, str) or not scenario_id:
                _fail(f"scenario[{index}] needs an id")
            telemetry = scenario.get("telemetry")
            if not isinstance(telemetry, Mapping):
                _fail(f"{scenario_id}: telemetry must be an object")
            filtered = _CONTRACT.validate_and_filter("telemetry_frame", telemetry)
            if filtered.get("module_id") not in WEATHER_IDS:
                _fail(f"{scenario_id}: unsupported module_id")
            if filtered.get("fallback_state") not in QUALITY_STATES:
                _fail(f"{scenario_id}: unsupported fallback state")
            _validate_display_only(scenario.get("display_only"), scenario_id)
            result["scenarios"][index]["telemetry"] = filtered
        return result
    except FixtureValidationError:
        raise
    except Exception as exc:
        raise FixtureValidationError(str(exc)) from exc


def load_and_validate_fixture(path: str | Path) -> dict[str, Any]:
    fixture_path = Path(path)
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureValidationError(str(exc)) from exc
    return validate_fixture(payload)
