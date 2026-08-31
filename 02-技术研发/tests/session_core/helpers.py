from __future__ import annotations

from dataclasses import replace
from typing import Any

from srp_session_core import (
    CallableGate,
    InMemoryManifestStore,
    RuntimeDependencies,
    load_protocol_config,
)
from srp_session_core.gates import CallableExposureGate, load_g02_privacy_gate


def formal_dependencies(exposure_calls: list[str] | None = None) -> RuntimeDependencies:
    calls = exposure_calls if exposure_calls is not None else []

    def pass_gate(manifest, assignment, config_hash):
        del manifest, assignment, config_hash
        return "formal-fixture:PASS"

    def exposure(manifest, assignment):
        del assignment
        calls.append(str(manifest["session_id"]))
        return "formal-exposure:PASS"

    return RuntimeDependencies(
        privacy_gate=load_g02_privacy_gate(),
        assignment_gate=CallableGate("assignment", pass_gate, formal_capable=True),
        formal_readiness_gate=CallableGate(
            "formal_readiness", pass_gate, formal_capable=True
        ),
        manifest_store=InMemoryManifestStore(formal_capable=True),
        exposure_gate=CallableExposureGate(exposure, formal_capable=True),
    )


def fast_transport_config(**changes: Any):
    config = load_protocol_config()
    transport = replace(
        config.transport,
        ack_timeout_ms=changes.pop("ack_timeout_ms", 30),
        reconnect_grace_ms=changes.pop("reconnect_grace_ms", 60),
        **changes,
    )
    return replace(config, transport=transport)


def ack_for(event, *, result="applied", error_code=None, now_ns=1):
    return {
        "schema_version": event["schema_version"],
        "message_type": "ack",
        "session_id": event["session_id"],
        "event_id": event["event_id"],
        "received_monotonic_ns": now_ns,
        "applied_monotonic_ns": now_ns,
        "unity_frame": 1,
        "result": result,
        "error_code": error_code,
    }


def telemetry_for(snapshot, *, frame_seq=1, sent_ns=50_000_000):
    schema_version = getattr(snapshot, "schema_version", "2.1")
    frame = {
        "schema_version": schema_version,
        "message_type": "telemetry_frame",
        "session_id": snapshot.session_id,
        "frame_seq": frame_seq,
        "clock_domain_id": f"python:{snapshot.session_id}",
        "source_monotonic_ns": sent_ns - 2,
        "received_monotonic_ns": sent_ns - 1,
        "sent_monotonic_ns": sent_ns,
        "clock_offset_ns": 0,
        "clock_drift_ppm": 0.0,
        "sync_uncertainty_ns": 0,
        "module_id": snapshot.module_id,
        "module_position": snapshot.module_position,
        "segment": snapshot.segment,
        "target_phase": "inhale",
        "target_progress": 0.25,
        "actual_phase": "inhale",
        "actual_progress": 0.2,
        "actual_confidence": 0.9,
        "recovery_value": 0.1,
        "recovery_locked": snapshot.segment == "lock_transition",
        "signal_quality": {"resp": 0.9, "ecg": 0.8},
        "fallback_state": "GOOD",
        "fallback_reason": None,
        "resp_device_state": "CONNECTED",
        "ecg_device_state": "CONNECTED",
        "cue_mode": snapshot.cue_mode,
        "runtime_mode": snapshot.runtime_mode,
        "policy_decision_id": "PD-P01-0",
    }
    if schema_version == "2.2":
        frame.update(
            target_cycle_index=0,
            target_step_id="inhale_1",
            actual_cycle_index=0,
            actual_step_id="inhale_1",
        )
    return frame
