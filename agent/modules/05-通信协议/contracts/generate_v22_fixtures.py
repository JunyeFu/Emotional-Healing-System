from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V21 = ROOT / "fixtures" / "valid"
V22 = ROOT / "fixtures-v2.2"
CONSUMERS = ROOT / "consumer-fixtures" / "v2.2"
BREATH_CONFIG = (
    ROOT.parent.parent / "srp_session_core" / "config" / "breath_protocol_config_v2.2.json"
)


def _read(name: str) -> dict:
    return json.loads((V21 / name).read_text(encoding="utf-8"))


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _telemetry(
    *,
    module_id: str,
    frame_seq: int,
    target_step_id: str | None,
    target_phase: str,
    actual_step_id: str | None,
    actual_phase: str,
    target_cycle_index: int | None = 0,
    actual_cycle_index: int | None = 0,
) -> dict:
    frame = _read("telemetry-frame.json")
    frame.update(
        schema_version="2.2",
        frame_seq=frame_seq,
        module_id=module_id,
        target_cycle_index=target_cycle_index,
        target_step_id=target_step_id,
        target_phase=target_phase,
        target_progress=0 if target_step_id is None else 0.4,
        actual_cycle_index=actual_cycle_index,
        actual_step_id=actual_step_id,
        actual_phase=actual_phase,
        actual_progress=0 if actual_step_id is None else 0.35,
    )
    frame["source_monotonic_ns"] = 2_000_000 + frame_seq * 100_000
    frame["received_monotonic_ns"] = frame["source_monotonic_ns"] + 50_000
    frame["sent_monotonic_ns"] = frame["received_monotonic_ns"] + 50_000
    return frame


def build() -> None:
    breath_payload = json.loads(BREATH_CONFIG.read_text(encoding="utf-8"))
    breath_hash = _canonical_hash(breath_payload)

    manifest = _read("session-manifest-formal.json")
    manifest.update(
        schema_version="2.2",
        breath_protocol_config_version="2.2",
        breath_protocol_config_hash=breath_hash,
    )
    _write(V22 / "valid" / "session-manifest-formal.json", manifest)

    for name in (
        "control-event.json",
        "ack.json",
        "policy-decision.json",
        "render-receipt.json",
    ):
        payload = _read(name)
        payload["schema_version"] = "2.2"
        _write(V22 / "valid" / name, payload)

    frames = {
        "telemetry-storm-hold-1.json": _telemetry(
            module_id="storm",
            frame_seq=20,
            target_step_id="hold_1",
            target_phase="hold",
            actual_step_id="inhale_1",
            actual_phase="inhale",
        ),
        "telemetry-storm-hold-2.json": _telemetry(
            module_id="storm",
            frame_seq=21,
            target_step_id="hold_2",
            target_phase="hold",
            actual_step_id="exhale_1",
            actual_phase="exhale",
        ),
        "telemetry-fade-inhale-1.json": _telemetry(
            module_id="fade",
            frame_seq=22,
            target_step_id="inhale_1",
            target_phase="inhale",
            actual_step_id="inhale_1",
            actual_phase="inhale",
        ),
        "telemetry-fade-inhale-2.json": _telemetry(
            module_id="fade",
            frame_seq=23,
            target_step_id="inhale_2",
            target_phase="inhale",
            actual_step_id="inhale_1",
            actual_phase="inhale",
        ),
        "telemetry-actual-unavailable.json": _telemetry(
            module_id="snow",
            frame_seq=24,
            target_step_id="exhale_1",
            target_phase="exhale",
            actual_step_id=None,
            actual_phase="none",
            actual_cycle_index=None,
        ),
    }
    for name, payload in frames.items():
        _write(V22 / "valid" / name, payload)

    invalid = {
        "telemetry-missing-step-id.json": deepcopy(frames["telemetry-storm-hold-1.json"]),
        "telemetry-partial-step-identity.json": deepcopy(frames["telemetry-storm-hold-1.json"]),
        "telemetry-step-phase-mismatch.json": deepcopy(frames["telemetry-fade-inhale-2.json"]),
        "telemetry-unknown-step.json": deepcopy(frames["telemetry-storm-hold-1.json"]),
        "telemetry-empty-step-state-mismatch.json": deepcopy(frames["telemetry-actual-unavailable.json"]),
        "telemetry-retired-calm-index.json": deepcopy(frames["telemetry-storm-hold-1.json"]),
        "session-manifest-invalid-breath-hash.json": deepcopy(manifest),
        "control-event-wrong-version.json": deepcopy(
            json.loads((V22 / "valid" / "control-event.json").read_text(encoding="utf-8"))
        ),
    }
    invalid["telemetry-missing-step-id.json"].pop("target_step_id")
    invalid["telemetry-partial-step-identity.json"]["target_cycle_index"] = None
    invalid["telemetry-step-phase-mismatch.json"]["target_phase"] = "exhale"
    invalid["telemetry-unknown-step.json"]["target_step_id"] = "inhale_9"
    invalid["telemetry-empty-step-state-mismatch.json"]["actual_phase"] = "inhale"
    invalid["telemetry-retired-calm-index.json"]["calm_index"] = 0.7
    invalid["session-manifest-invalid-breath-hash.json"]["breath_protocol_config_hash"] = "sha256:not-a-hash"
    invalid["control-event-wrong-version.json"]["schema_version"] = "2.1"
    for name, payload in invalid.items():
        _write(V22 / "invalid" / name, payload)

    ordered_frames = [frames[name] for name in (
        "telemetry-storm-hold-1.json",
        "telemetry-storm-hold-2.json",
        "telemetry-fade-inhale-1.json",
        "telemetry-fade-inhale-2.json",
        "telemetry-actual-unavailable.json",
    )]
    for consumer in ("unity", "touchdesigner"):
        path = CONSUMERS / consumer / "phase-instance-stream.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(
                json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
                for item in ordered_frames
            ),
            encoding="utf-8",
            newline="\n",
        )
    _write(
        CONSUMERS / "unity" / "hello-v2.2.json",
        {
            "transport_type": "hello",
            "transport_version": "1.0",
            "role": "unity",
            "schema_version": "2.2",
            "client_instance_id": "unity-f05-fixture",
        },
    )
    _write(
        CONSUMERS / "unity" / "hello-v2.1-formal-rejected.json",
        {
            "transport_type": "hello",
            "transport_version": "1.0",
            "role": "unity",
            "schema_version": "2.1",
            "client_instance_id": "unity-unmigrated-fixture",
            "expected_error_code": "SCHEMA_VERSION_MISMATCH",
        },
    )


if __name__ == "__main__":
    build()
