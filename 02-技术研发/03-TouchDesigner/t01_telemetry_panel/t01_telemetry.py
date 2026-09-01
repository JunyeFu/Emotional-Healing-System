"""Read-only telemetry state for the T-01 TouchDesigner panel."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Mapping


if "project" in globals():
    TECH_ROOT = Path(project.folder).resolve().parents[1]
else:
    TECH_ROOT = Path(__file__).resolve().parents[2]
if str(TECH_ROOT) not in sys.path:
    sys.path.insert(0, str(TECH_ROOT))

from srp_session_core.contract_adapter import validate_message  # noqa: E402
from srp_session_core.errors import SessionCoreError  # noqa: E402


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class IngestResult:
    accepted: bool
    disposition: str
    code: str | None = None


@dataclass(frozen=True, slots=True)
class TelemetryPanelSnapshot:
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


class T01TelemetryAdapter:
    """Validate UDP datagrams and expose a throttled immutable display snapshot."""

    def __init__(
        self,
        *,
        telemetry_hz: int = 20,
        disconnect_timeout_ns: int = 2_000_000_000,
    ) -> None:
        if telemetry_hz <= 0 or disconnect_timeout_ns <= 0:
            raise ValueError("telemetry_hz and disconnect_timeout_ns must be positive")
        self.render_interval_ns = round(1_000_000_000 / telemetry_hz)
        self.disconnect_timeout_ns = disconnect_timeout_ns
        self._latest: dict[str, Any] | None = None
        self._epoch: tuple[str, str] | None = None
        self._epoch_index = 0
        self._last_seq: int | None = None
        self._last_accepted_ns: int | None = None
        self._previous_accepted_ns: int | None = None
        self._last_render_ns: int | None = None
        self._cached_snapshot: TelemetryPanelSnapshot | None = None
        self._last_render_state: str | None = None
        self._last_disposition = "WAITING"
        self._last_error: str | None = None
        self._accepted_frames = 0
        self._lost_frames = 0
        self._duplicate_frames = 0
        self._out_of_order_frames = 0
        self._invalid_frames = 0
        self._reconnect_count = 0
        self._session_change_count = 0
        self._source_restart_count = 0

    def ingest_datagram(self, raw: bytes | str, received_monotonic_ns: int) -> IngestResult:
        if isinstance(received_monotonic_ns, bool) or not isinstance(received_monotonic_ns, int) or received_monotonic_ns < 0:
            raise ValueError("received_monotonic_ns must be a non-negative integer")
        try:
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        except UnicodeDecodeError:
            return self._reject("INVALID_ENCODING")
        if not isinstance(text, str):
            return self._reject("INVALID_DATAGRAM_TYPE")
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return self._reject("INVALID_JSON")
        if not isinstance(payload, Mapping):
            return self._reject("INVALID_JSON_OBJECT")
        try:
            validated = validate_message("telemetry_frame", payload)
        except SessionCoreError as error:
            return self._reject(error.code)
        if (
            validated["schema_version"] == "2.1"
            and str(validated["runtime_mode"]).startswith("formal_")
        ):
            return self._reject("FORMAL_V21_REJECTED")

        epoch = (str(validated["session_id"]), str(validated["clock_domain_id"]))
        if self._epoch != epoch:
            if self._epoch is not None:
                if self._epoch[0] != epoch[0]:
                    self._session_change_count += 1
                else:
                    self._source_restart_count += 1
            self._epoch = epoch
            self._epoch_index += 1
            self._last_seq = None

        frame_seq = int(validated["frame_seq"])
        if self._last_seq is not None and frame_seq == self._last_seq:
            self._duplicate_frames += 1
            self._last_disposition = "DUPLICATE"
            self._last_error = "DUPLICATE_SEQUENCE"
            return IngestResult(False, "DUPLICATE", "DUPLICATE_SEQUENCE")
        if self._last_seq is not None and frame_seq < self._last_seq:
            self._out_of_order_frames += 1
            self._last_disposition = "OUT_OF_ORDER"
            self._last_error = "OUT_OF_ORDER_SEQUENCE"
            return IngestResult(False, "OUT_OF_ORDER", "OUT_OF_ORDER_SEQUENCE")

        disposition = "ACCEPTED"
        if self._last_seq is not None and frame_seq > self._last_seq + 1:
            self._lost_frames += frame_seq - self._last_seq - 1
            disposition = "ACCEPTED_WITH_GAP"
        if self._is_disconnected(received_monotonic_ns):
            self._reconnect_count += 1
        self._last_seq = frame_seq
        self._latest = deepcopy(validated)
        self._previous_accepted_ns = self._last_accepted_ns
        self._last_accepted_ns = received_monotonic_ns
        self._accepted_frames += 1
        self._last_disposition = disposition
        self._last_error = None
        return IngestResult(True, disposition)

    def read_snapshot(self, now_ns: int) -> TelemetryPanelSnapshot:
        if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
            raise ValueError("now_ns must be a non-negative integer")
        state = self._stream_state(now_ns)
        throttled = (
            self._cached_snapshot is not None
            and self._last_render_ns is not None
            and now_ns - self._last_render_ns < self.render_interval_ns
        )
        if throttled:
            return self._cached_snapshot
        snapshot = self._build_snapshot(now_ns, state)
        self._cached_snapshot = snapshot
        self._last_render_ns = now_ns
        self._last_render_state = state
        return snapshot

    def _reject(self, code: str) -> IngestResult:
        self._invalid_frames += 1
        self._last_disposition = "INVALID"
        self._last_error = code
        return IngestResult(False, "INVALID", code)

    def _is_disconnected(self, now_ns: int) -> bool:
        return (
            self._last_accepted_ns is not None
            and now_ns - self._last_accepted_ns >= self.disconnect_timeout_ns
        )

    def _stream_state(self, now_ns: int) -> str:
        if self._last_accepted_ns is None:
            return "WAITING"
        return "DISCONNECTED" if self._is_disconnected(now_ns) else "LIVE"

    def _build_snapshot(self, now_ns: int, state: str) -> TelemetryPanelSnapshot:
        telemetry = self._latest or {}
        age_ms = (
            None
            if self._last_accepted_ns is None
            else round((now_ns - self._last_accepted_ns) / 1_000_000, 3)
        )
        interval_ms = (
            None
            if self._previous_accepted_ns is None or self._last_accepted_ns is None
            else round((self._last_accepted_ns - self._previous_accepted_ns) / 1_000_000, 3)
        )
        target_step = telemetry.get("target_step_id")
        actual_step = telemetry.get("actual_step_id")
        timing = self._timing(telemetry)
        snapshot = TelemetryPanelSnapshot(
            meta=_freeze(
                {
                    "stream_state": state,
                    "epoch_index": self._epoch_index,
                    "source_mode": telemetry.get("runtime_mode", "UNAVAILABLE"),
                    "banner": self._banner(telemetry),
                }
            ),
            telemetry=_freeze(telemetry),
            display_only=_freeze(
                {
                    "transport": {
                        "accepted_frames": self._accepted_frames,
                        "lost_frames": self._lost_frames,
                        "duplicate_frames": self._duplicate_frames,
                        "out_of_order_frames": self._out_of_order_frames,
                        "invalid_frames": self._invalid_frames,
                        "reconnect_count": self._reconnect_count,
                        "session_change_count": self._session_change_count,
                        "source_restart_count": self._source_restart_count,
                        "last_error": self._last_error,
                        "last_disposition": self._last_disposition,
                        "frame_age_ms": age_ms,
                        "accepted_interval_ms": interval_ms,
                    },
                    "phase_identity": {
                        "target_cycle": telemetry.get("target_cycle_index", "UNAVAILABLE"),
                        "target_step": target_step if target_step is not None else "UNAVAILABLE",
                        "actual_cycle": telemetry.get("actual_cycle_index", "UNAVAILABLE"),
                        "actual_step": actual_step if actual_step is not None else "UNAVAILABLE",
                    },
                    "timing": timing,
                }
            ),
        )
        return snapshot

    @staticmethod
    def _timing(telemetry: Mapping[str, Any]) -> dict[str, Any]:
        required = ("source_monotonic_ns", "received_monotonic_ns", "sent_monotonic_ns")
        if not all(key in telemetry for key in required):
            return {
                "source_to_received_ms": None,
                "received_to_sent_ms": None,
                "source_to_sent_ms": None,
                "clock_offset_ns": None,
                "clock_drift_ppm": None,
                "sync_uncertainty_ns": None,
            }
        source = int(telemetry["source_monotonic_ns"])
        received = int(telemetry["received_monotonic_ns"])
        sent = int(telemetry["sent_monotonic_ns"])
        return {
            "source_to_received_ms": round((received - source) / 1_000_000, 6),
            "received_to_sent_ms": round((sent - received) / 1_000_000, 6),
            "source_to_sent_ms": round((sent - source) / 1_000_000, 6),
            "clock_offset_ns": telemetry["clock_offset_ns"],
            "clock_drift_ppm": telemetry["clock_drift_ppm"],
            "sync_uncertainty_ns": telemetry["sync_uncertainty_ns"],
        }

    @staticmethod
    def _banner(telemetry: Mapping[str, Any]) -> str:
        if telemetry.get("runtime_mode") == "dev_replay":
            return "READ ONLY / DEV-REPLAY / NOT LIVE"
        return "READ ONLY / LIVE TELEMETRY / PYTHON AUTHORITY"


def snapshot_to_dict(snapshot: TelemetryPanelSnapshot) -> dict[str, Any]:
    """Return a JSON-serializable copy for local DAT display and evidence."""
    return {
        "meta": _to_plain(snapshot.meta),
        "telemetry": _to_plain(snapshot.telemetry),
        "display_only": _to_plain(snapshot.display_only),
    }


def _to_plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    return deepcopy(value)


def snapshot_to_panel_text(snapshot: TelemetryPanelSnapshot) -> str:
    telemetry = snapshot.telemetry
    display = snapshot.display_only
    transport = display["transport"]
    identity = display["phase_identity"]
    timing = display["timing"]
    quality = telemetry.get("signal_quality", {})

    def value(key: str) -> Any:
        item = telemetry.get(key)
        return "UNAVAILABLE" if item is None else item

    return "\n".join(
        [
            "T-01 TELEMETRY / DEVICE QUALITY / CLOCK",
            str(snapshot.meta["banner"]),
            "",
            f"STREAM {snapshot.meta['stream_state']}   SESSION {value('session_id')}   SCHEMA {value('schema_version')}",
            f"RUNTIME {value('runtime_mode')}   FRAME {value('frame_seq')}   AGE {transport['frame_age_ms']} ms",
            "",
            f"RESP {value('resp_device_state')}   SQI {quality.get('resp', 'UNAVAILABLE')}",
            f"ECG  {value('ecg_device_state')}   SQI {quality.get('ecg', 'UNAVAILABLE')}",
            "",
            f"TARGET CYCLE {identity['target_cycle']}   STEP {identity['target_step']}   PHASE {value('target_phase')}   PROGRESS {value('target_progress')}",
            f"ACTUAL CYCLE {identity['actual_cycle']}   STEP {identity['actual_step']}   PHASE {value('actual_phase')}   PROGRESS {value('actual_progress')}",
            "",
            f"PIPELINE source->received {timing['source_to_received_ms']} ms   received->sent {timing['received_to_sent_ms']} ms",
            f"CLOCK offset {timing['clock_offset_ns']} ns   drift {timing['clock_drift_ppm']} ppm   uncertainty {timing['sync_uncertainty_ns']} ns",
            "",
            f"SEQ accepted {transport['accepted_frames']}   lost {transport['lost_frames']}   duplicate {transport['duplicate_frames']}   out-of-order {transport['out_of_order_frames']}",
            f"LINK invalid {transport['invalid_frames']}   reconnect {transport['reconnect_count']}   last {transport['last_disposition']}   error {transport['last_error'] or 'NONE'}",
            "",
            f"PYTHON FALLBACK {value('fallback_state')}   REASON {value('fallback_reason')}",
            "LOCAL LINK STATE IS DISPLAY-ONLY / NO AUTHORITY WRITEBACK / T-02 NOT ACTIVE",
        ]
    )
