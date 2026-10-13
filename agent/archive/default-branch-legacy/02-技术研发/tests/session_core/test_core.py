from __future__ import annotations

from itertools import permutations
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from srp_session_core import (
    OperatorRequest,
    SessionCore,
    SessionCoreError,
    SessionStatus,
)

from .helpers import ack_for, formal_dependencies


WEATHERS = ("storm", "heat", "snow", "fade")


def _run_exact_session(core: SessionCore, start_ns: int) -> None:
    now = start_ns
    for _ in range(4):
        for duration_ns in (25_000_000_000, 150_000_000_000, 25_000_000_000):
            now += duration_ns
            update = core.advance(now)
            for event in update.control_events:
                if event["event_type"] == "end":
                    core.confirm_delivery(ack_for(event, now_ns=now), now)


@pytest.mark.parametrize("sequence", list(permutations(WEATHERS)))
@pytest.mark.parametrize("cue_mode", ["scene_native", "abstract_pacer"])
def test_all_sequences_and_cue_modes_finish_once_each(
    manifest_factory, assignment_factory, sequence, cue_mode
) -> None:
    manifest = manifest_factory(sequence=sequence, cue_mode=cue_mode)
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    start = core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)

    assert [event["event_type"] for event in start.control_events] == [
        "start", "module", "segment"
    ]
    _run_exact_session(core, 0)
    summary = core.finish("COMPLETED", 800_000_000_000)

    assert summary.status is SessionStatus.COMPLETED
    assert summary.completed_modules == sequence
    assert summary.session_elapsed_ns == 800_000_000_000
    assert len(set(summary.completed_modules)) == 4


def test_late_end_ack_cannot_reverse_aborted_terminal_state(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory(runtime_mode="formal_stage_1")
    core = SessionCore(dependencies=formal_dependencies())
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    core.confirm_delivery(ack_for(prepared.control_events[0], now_ns=0), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    now = 0
    final = None
    for duration_ns in (25_000_000_000, 150_000_000_000, 25_000_000_000) * 4:
        now += duration_ns
        final = core.advance(now)
    end = final.control_events[-1]
    core.transport_failure("CONTROL_ACK_TIMEOUT", now + 1)

    late = core.confirm_delivery(ack_for(end, now_ns=now + 2), now + 2)

    assert late.snapshot.status is SessionStatus.ABORTED
    assert late.audit_records[-1].reason_code == "SESSION_TERMINAL"
    assert "session_completed" not in {
        event.event_type for event in core.session_event_log
    }
    assert late.snapshot.session_elapsed_ns == 800_000_000_001


def test_end_ack_wait_allows_abort_and_development_transport_pause(
    manifest_factory, assignment_factory
) -> None:
    for runtime_mode, expected_status in (
        ("formal_stage_1", SessionStatus.ABORTED),
        ("dev_replay", SessionStatus.PAUSED),
    ):
        dependencies = formal_dependencies() if runtime_mode.startswith("formal_") else None
        core = SessionCore(dependencies=dependencies)
        manifest = manifest_factory(runtime_mode=runtime_mode)
        prepared = core.prepare(manifest, assignment_factory(manifest), 0)
        if runtime_mode.startswith("formal_"):
            core.confirm_delivery(ack_for(prepared.control_events[0], now_ns=0), 0)
        core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
        now = 0
        for duration_ns in (25_000_000_000, 150_000_000_000, 25_000_000_000) * 4:
            now += duration_ns
            core.advance(now)

        if runtime_mode.startswith("formal_"):
            update = core.apply_operator_request(
                OperatorRequest("REQ-ABORT-END", "abort"), now + 1
            )
        else:
            update = core.transport_failure("CONTROL_ACK_TIMEOUT", now + 1)

        assert update.snapshot.status is expected_status


def test_terminal_elapsed_time_is_immutable_after_late_inputs(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    now = 0
    final = None
    for duration_ns in (25_000_000_000, 150_000_000_000, 25_000_000_000) * 4:
        now += duration_ns
        final = core.advance(now)
    end = final.control_events[-1]
    core.confirm_delivery(ack_for(end, now_ns=now), now)
    expected = core.snapshot().session_elapsed_ns

    core.confirm_delivery(ack_for(end, now_ns=now + 100_000_000_000), now + 100_000_000_000)
    summary = core.finish("COMPLETED", now + 200_000_000_000)

    assert core.snapshot().session_elapsed_ns == expected
    assert summary.session_elapsed_ns == expected


def test_v22_session_rejects_v21_delivery_message(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory(schema_version="2.2")
    core = SessionCore()
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    ack = ack_for(prepared.control_events[0], now_ns=1)
    ack["schema_version"] = "2.1"
    with pytest.raises(SessionCoreError) as error:
        core.confirm_delivery(ack, 1)
    assert error.value.code == "SCHEMA_VERSION_MISMATCH"


def test_duplicate_request_and_repeated_tick_do_not_advance(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    request = OperatorRequest("REQ-START", "start")
    first = core.apply_operator_request(request, 0)
    duplicate = core.apply_operator_request(request, 0)
    boundary = core.advance(25_000_000_000)
    repeated = core.advance(25_000_000_000)

    assert first.snapshot.status is SessionStatus.RUNNING
    assert duplicate.control_events == ()
    assert duplicate.audit_records[0].result == "rejected"
    assert duplicate.audit_records[0].reason_code == "DUPLICATE_OPERATOR_REQUEST"
    assert len(boundary.control_events) == 1
    assert repeated.control_events == ()
    assert repeated.snapshot.segment == "closed_loop"


def test_illegal_transition_is_rejected_without_state_change(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)

    update = core.apply_operator_request(OperatorRequest("REQ-PAUSE", "pause"), 0)

    assert update.snapshot.status is SessionStatus.PREPARED
    assert update.control_events == ()
    assert update.audit_records[0].reason_code == "ILLEGAL_TRANSITION"


def test_pause_freezes_progress_and_resume_shifts_deadline(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    core.advance(10_000_000_000)
    paused = core.apply_operator_request(
        OperatorRequest("REQ-PAUSE", "pause", "OPERATOR_PAUSE"), 10_000_000_000
    )
    core.advance(110_000_000_000)
    frozen = core.snapshot()
    resumed = core.apply_operator_request(OperatorRequest("REQ-RESUME", "start"), 110_000_000_000)

    assert paused.snapshot.segment_progress == pytest.approx(0.4)
    assert frozen.segment_progress == pytest.approx(0.4)
    assert resumed.snapshot.paused_duration_ns == 100_000_000_000
    assert core.advance(124_999_999_999).control_events == ()
    assert core.advance(125_000_000_000).snapshot.segment == "closed_loop"


def test_v22_pause_resume_preserves_identity_and_duplicate_is_idempotent(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory(schema_version="2.2")
    core = SessionCore()
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    initial = prepared.snapshot
    core.apply_operator_request(OperatorRequest("REQ-V22-START", "start"), 1)
    paused = core.apply_operator_request(OperatorRequest("REQ-V22-PAUSE", "pause"), 2)
    duplicate = core.apply_operator_request(OperatorRequest("REQ-V22-PAUSE", "pause"), 3)
    resumed = core.apply_operator_request(OperatorRequest("REQ-V22-RESUME", "start"), 4)

    expected_identity = (
        "2.2",
        "2.2",
        "sha256:e5bb3c609f069a31bf9d02af1c987ccafc2be8d4fd01ca2394565c0c10d4a203",
    )
    for snapshot in (initial, paused.snapshot, duplicate.snapshot, resumed.snapshot):
        assert (
            snapshot.schema_version,
            snapshot.breath_protocol_config_version,
            snapshot.breath_protocol_config_hash,
        ) == expected_identity
    assert duplicate.snapshot.status is SessionStatus.PAUSED
    assert duplicate.control_events == ()
    assert duplicate.audit_records[0].reason_code == "DUPLICATE_OPERATOR_REQUEST"


def test_non_monotonic_clock_fails_and_audits(manifest_factory, assignment_factory) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 10)

    with pytest.raises(SessionCoreError) as error:
        core.advance(9)

    assert error.value.code == "NON_MONOTONIC_CLOCK"
    assert core.audit_log[-1].reason_code == "NON_MONOTONIC_CLOCK"


def test_formal_start_requires_prepare_ack_and_marks_exposure_once(
    manifest_factory, assignment_factory
) -> None:
    calls: list[str] = []
    manifest = manifest_factory(runtime_mode="formal_stage_1")
    core = SessionCore(dependencies=formal_dependencies(calls))
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    rejected = core.apply_operator_request(OperatorRequest("REQ-EARLY", "start"), 0)
    prepare_event = prepared.control_events[0]
    core.confirm_delivery(ack_for(prepare_event, now_ns=1), 1)
    started = core.apply_operator_request(OperatorRequest("REQ-START", "start"), 1)
    duplicate = core.apply_operator_request(OperatorRequest("REQ-START", "start"), 1)

    assert rejected.audit_records[0].reason_code == "PREPARE_ACK_REQUIRED"
    assert started.snapshot.status is SessionStatus.RUNNING
    assert calls == [manifest["session_id"]]
    assert duplicate.audit_records[0].result == "rejected"


def test_formal_scheduler_lag_aborts(manifest_factory, assignment_factory) -> None:
    manifest = manifest_factory(runtime_mode="formal_stage_1")
    core = SessionCore(dependencies=formal_dependencies())
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    core.confirm_delivery(ack_for(prepared.control_events[0], now_ns=0), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)

    update = core.advance(25_201_000_000)

    assert update.snapshot.status is SessionStatus.ABORTED
    assert update.control_events[-1]["event_type"] == "abort"
    assert update.session_events[-1].reason_code == "SCHEDULER_LAG_EXCEEDED"


@pytest.mark.parametrize(
    ("field", "wrong_value", "reason_code"),
    [
        ("module_id", "heat", "RENDER_RECEIPT_MODULE_MISMATCH"),
        ("segment", "closed_loop", "RENDER_RECEIPT_SEGMENT_MISMATCH"),
    ],
)
def test_render_receipt_must_match_acknowledged_segment_control(
    field, wrong_value, reason_code, manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    started = core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    segment = started.control_events[2]
    core.confirm_delivery(ack_for(segment, now_ns=1), 1)
    receipt = {
        "schema_version": "2.1",
        "message_type": "render_receipt",
        "receipt_id": f"RR-MISMATCH-{field}",
        "session_id": manifest["session_id"],
        "event_id": segment["event_id"],
        "frame_seq": 1,
        "unity_frame": 1,
        "rendered_monotonic_ns": 2,
        "module_id": segment["payload"]["module_id"],
        "segment": segment["payload"]["segment"],
        "result": "rendered",
        "error_code": None,
    }
    receipt[field] = wrong_value

    update = core.confirm_delivery(receipt, 2)

    assert update.audit_records[0].result == "rejected"
    assert update.audit_records[0].reason_code == reason_code
    assert not update.session_events


def test_render_receipt_requires_acknowledged_control(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    segment = core.apply_operator_request(
        OperatorRequest("REQ-START", "start"), 0
    ).control_events[2]
    receipt = {
        "schema_version": "2.1",
        "message_type": "render_receipt",
        "receipt_id": "RR-EARLY",
        "session_id": manifest["session_id"],
        "event_id": segment["event_id"],
        "frame_seq": 1,
        "unity_frame": 1,
        "rendered_monotonic_ns": 1,
        "module_id": segment["payload"]["module_id"],
        "segment": segment["payload"]["segment"],
        "result": "rendered",
        "error_code": None,
    }

    update = core.confirm_delivery(receipt, 1)

    assert update.audit_records[0].reason_code == "CONTROL_NOT_ACKNOWLEDGED"
    assert not update.session_events


def test_unity_receipt_identity_is_idempotent_per_instance_and_distinct_across_instances(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    segment = core.apply_operator_request(
        OperatorRequest("REQ-START", "start"), 0
    ).control_events[2]
    core.confirm_delivery(ack_for(segment, now_ns=1), 1)

    def receipt(instance: str) -> dict:
        return {
            "schema_version": "2.1",
            "message_type": "render_receipt",
            "receipt_id": f"RR-{instance}-{segment['event_id']}",
            "session_id": manifest["session_id"],
            "event_id": segment["event_id"],
            "frame_seq": 1,
            "unity_frame": 1,
            "rendered_monotonic_ns": 2,
            "module_id": segment["payload"]["module_id"],
            "segment": segment["payload"]["segment"],
            "result": "rendered",
            "error_code": None,
        }

    first = core.confirm_delivery(receipt("unity-a"), 2)
    duplicate = core.confirm_delivery(receipt("unity-a"), 3)
    second_instance = core.confirm_delivery(receipt("unity-b"), 4)

    assert len(first.session_events) == 1
    assert not duplicate.session_events
    assert duplicate.audit_records[0].reason_code == "DUPLICATE_RENDER_RECEIPT"
    assert len(second_instance.session_events) == 1
    assert second_instance.audit_records[0].result == "applied"


def test_session_events_validate_against_machine_schema(
    manifest_factory, assignment_factory
) -> None:
    manifest = manifest_factory()
    core = SessionCore()
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 0)
    core.advance(25_000_000_000)
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "srp_session_core"
        / "contracts"
        / "session-event-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    for event in core.session_event_log:
        validator.validate(event.to_dict())


def test_committed_golden_trace_is_deterministic() -> None:
    from srp_session_core.generate_golden_trace import build_trace

    path = (
        Path(__file__).resolve().parents[2]
        / "srp_session_core"
        / "fixtures"
        / "golden"
        / "four-module-trace-v1.json"
    )
    committed = json.loads(path.read_text(encoding="utf-8"))

    assert build_trace() == committed
    assert committed["summary"]["status"] == "COMPLETED"
    assert committed["summary"]["session_elapsed_ns"] == 800_000_000_000
    assert len(committed["control_events"]) == 19
    assert len(committed["policy_decisions"]) == 4
