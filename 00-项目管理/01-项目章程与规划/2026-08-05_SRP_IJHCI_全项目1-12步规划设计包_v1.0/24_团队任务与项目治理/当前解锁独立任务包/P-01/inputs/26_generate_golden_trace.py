from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from srp_session_core import AssignmentBundle, OperatorRequest, SessionCore


def _manifest() -> dict[str, Any]:
    return {
        "schema_version": "2.1",
        "message_type": "session_manifest",
        "research_id": "SRP-R-GOLDEN-0001",
        "session_id": "S-P01-GOLDEN-0001",
        "study_stage": "stage_1",
        "runtime_mode": "dev_replay",
        "cue_mode": "scene_native",
        "assignment_arm": "scene_native",
        "allocation_index": 1,
        "randomization_stratum": "golden_fixture",
        "randomization_block": 1,
        "randomization_list_hash": "sha256:p01-golden-list",
        "weather_sequence": ["storm", "heat", "snow", "fade"],
        "module_durations": {
            "demo": 25,
            "closed_loop": 150,
            "lock_transition": 25,
        },
        "protocol_config_version": "1.1",
        "randomization_version": "1.0",
        "strategy_version": None,
        "device_config": {
            "resp": {"source": "none"},
            "ecg": {"source": "none"},
        },
        "unity_build_hash": "sha256:p01-golden-unity",
        "python_commit": "p01-golden-generator",
        "td_build_hash": None,
        "source_policy": "replay",
        "created_utc": "2026-08-13T00:00:00Z",
    }


def _assignment(manifest: Mapping[str, Any]) -> AssignmentBundle:
    sequence = tuple(manifest["weather_sequence"])
    remaining = list(sequence)
    decisions = []
    for position, selected in enumerate(sequence):
        candidates = list(remaining)
        decisions.append({
            "schema_version": "2.1",
            "message_type": "policy_decision",
            "decision_id": f"PD-GOLDEN-{position}",
            "session_id": manifest["session_id"],
            "stage": "stage_1",
            "position": position,
            "candidate_actions": candidates,
            "selected_action": selected,
            "behavior_probability": 1 / len(candidates),
            "target_policy_probability": None,
            "state_snapshot_hash": f"sha256:golden-state-{position}",
            "random_draw": position / 10,
            "reason_code": "GOLDEN_FIXED_SEQUENCE",
            "fallback_applied": False,
            "fallback_reason": None,
            "policy_version": None,
            "created_monotonic_ns": position,
        })
        remaining.remove(selected)
    return AssignmentBundle(
        allocation_index=int(manifest["allocation_index"]),
        randomization_list_hash=str(manifest["randomization_list_hash"]),
        weather_sequence=sequence,
        policy_decisions=tuple(decisions),
        permit_id="GOLDEN-PERMIT",
        reservation_id="GOLDEN-RESERVATION",
    )


def _ack(event: Mapping[str, Any], now_ns: int) -> dict[str, Any]:
    return {
        "schema_version": "2.1",
        "message_type": "ack",
        "session_id": event["session_id"],
        "event_id": event["event_id"],
        "received_monotonic_ns": now_ns,
        "applied_monotonic_ns": now_ns,
        "unity_frame": int(event["control_seq"]),
        "result": "applied",
        "error_code": None,
    }


def _receipt(event: Mapping[str, Any], now_ns: int) -> dict[str, Any] | None:
    payload = event["payload"]
    if event["event_type"] != "segment":
        return None
    return {
        "schema_version": "2.1",
        "message_type": "render_receipt",
        "receipt_id": f"RR-GOLDEN-{event['control_seq']:06d}",
        "session_id": event["session_id"],
        "event_id": event["event_id"],
        "frame_seq": int(event["control_seq"]),
        "unity_frame": int(event["control_seq"]),
        "rendered_monotonic_ns": now_ns,
        "module_id": payload["module_id"],
        "segment": payload["segment"],
        "result": "rendered",
        "error_code": None,
    }


def _record_delivery(
    core: SessionCore,
    controls: list[Mapping[str, Any]],
    acks: list[Mapping[str, Any]],
    receipts: list[Mapping[str, Any]],
    events: tuple[Mapping[str, Any], ...],
    now_ns: int,
) -> None:
    for event in events:
        controls.append(dict(event))
        ack = _ack(event, now_ns)
        acks.append(ack)
        core.confirm_delivery(ack, now_ns)
        receipt = _receipt(event, now_ns)
        if receipt is not None:
            receipts.append(receipt)
            core.confirm_delivery(receipt, now_ns)


def build_trace() -> dict[str, Any]:
    manifest = _manifest()
    assignment = _assignment(manifest)
    core = SessionCore()
    controls: list[Mapping[str, Any]] = []
    acks: list[Mapping[str, Any]] = []
    receipts: list[Mapping[str, Any]] = []
    policy_decisions: list[Mapping[str, Any]] = []

    prepared = core.prepare(manifest, assignment, 0)
    _record_delivery(core, controls, acks, receipts, prepared.control_events, 0)
    started = core.apply_operator_request(
        OperatorRequest("REQ-GOLDEN-START", "start"), 1_000_000_000
    )
    policy_decisions.extend(started.policy_decisions)
    _record_delivery(
        core, controls, acks, receipts, started.control_events, 1_000_000_000
    )

    now_ns = 1_000_000_000
    for _ in range(4):
        for seconds in (25, 150, 25):
            now_ns += seconds * 1_000_000_000
            update = core.advance(now_ns)
            policy_decisions.extend(update.policy_decisions)
            _record_delivery(
                core, controls, acks, receipts, update.control_events, now_ns
            )
    summary = core.finish("COMPLETED", now_ns)
    payload = {
        "fixture_schema_version": "1.0",
        "evidence_status": "P01_TECHNICAL_CANDIDATE",
        "manifest": manifest,
        "assignment": {
            "allocation_index": assignment.allocation_index,
            "randomization_list_hash": assignment.randomization_list_hash,
            "weather_sequence": list(assignment.weather_sequence),
            "permit_id": assignment.permit_id,
            "reservation_id": assignment.reservation_id,
        },
        "protocol_config_hash": core.config.config_hash,
        "control_events": controls,
        "acks": acks,
        "render_receipts": receipts,
        "policy_decisions": policy_decisions,
        "session_events": [event.to_dict() for event in core.session_event_log],
        "audit_records": [record.to_dict() for record in core.audit_log],
        "summary": summary.to_dict(),
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    payload["trace_hash"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    output = Path(__file__).with_name("fixtures") / "golden" / "four-module-trace-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_trace(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
