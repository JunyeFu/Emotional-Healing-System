from __future__ import annotations

import json
from pathlib import Path

import pytest

from srp_session_core import (
    InMemoryManifestStore,
    OperatorRequest,
    RuntimeDependencies,
    SessionCore,
    TransportError,
)
from srp_session_store import (
    DurableManifestStore,
    RecordingSessionCore,
    ReplayReader,
    RecordingTelemetryPublisher,
    SessionReplayer,
    StoreError,
)


def build_recording_core(tmp_path: Path):
    store = DurableManifestStore.development(tmp_path)
    dependencies = RuntimeDependencies.development()
    dependencies.manifest_store = store
    return RecordingSessionCore(SessionCore(dependencies=dependencies), store), store


def test_manifest_store_returns_nonformal_receipt_in_development(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    update = core.prepare(manifest, assignment_factory(manifest), 0)
    receipt = next(item for item in update.gate_receipts if item.gate == "manifest_store")
    assert receipt.formal_capable is False
    assert receipt.evidence_id.startswith("p02:manifest:")
    assert store.archive is not None
    store.archive.close()


def test_recording_core_replays_to_identical_outputs(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    assignment = assignment_factory(manifest)
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment, 0)
    core.confirm_delivery(
        {
            "schema_version": "2.1",
            "message_type": "ack",
            "session_id": manifest["session_id"],
            "event_id": f"{manifest['session_id']}:control:000001",
            "received_monotonic_ns": 1,
            "applied_monotonic_ns": 2,
            "unity_frame": 1,
            "result": "applied",
            "error_code": None,
        },
        2,
    )
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 3)
    summary = core.finish("TEST_COMPLETE", 4)
    store.archive.seal(summary, 4)
    store.archive.close()

    reader = ReplayReader.open(tmp_path, manifest["session_id"])
    report = SessionReplayer(reader).replay_core()
    assert report.valid
    assert report.operation_count == 4
    assert report.expected_final_hash == report.actual_final_hash


def test_operation_is_durable_before_control_is_observable(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    update = core.prepare(manifest, assignment_factory(manifest), 0)
    records = list(ReplayReader.open(tmp_path, manifest["session_id"]).iter_l1())
    commit = next(item for item in records if item["record_type"] == "operation_commit")
    assert commit["payload"]["output"]["control_events"] == [dict(update.control_events[0])]
    assert any(item["record_type"] == "control_event" for item in records)
    assert any(item["record_type"] == "gate_receipt" for item in records)
    store.archive.close()


def test_formal_manifest_store_fails_without_environment(monkeypatch, manifest_factory):
    monkeypatch.delenv("SRP_SESSION_DATA_ROOT", raising=False)
    monkeypatch.delenv("SRP_SESSION_WRITER_ACCOUNT", raising=False)
    with pytest.raises(StoreError, match="FORMAL_STORAGE_UNAVAILABLE"):
        DurableManifestStore.from_formal_environment(Path.cwd())


def test_formal_manifest_store_requires_g02_environment_checks(monkeypatch, tmp_path):
    import srp_session_store.adapters as adapters

    monkeypatch.setenv("SRP_SESSION_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("SRP_SESSION_WRITER_ACCOUNT", "p02-writer")
    monkeypatch.setenv("SRP_SESSION_WRITER_ROLE", "primary_operator")
    monkeypatch.setattr(adapters, "_system_account", lambda: "p02-writer")
    monkeypatch.setattr(
        adapters,
        "_formal_environment_checks",
        lambda path, account, role: (
            path == tmp_path
            and account == "p02-writer"
            and role == "primary_operator"
        ),
    )
    store = DurableManifestStore.from_formal_environment(
        Path(__file__).resolve().parents[3]
    )
    assert store.formal_capable is True


def test_formal_manifest_store_has_no_public_probe_bypass():
    import inspect

    parameters = inspect.signature(
        DurableManifestStore.from_formal_environment
    ).parameters
    assert set(parameters) == {"repo_root"}


def test_formal_manifest_store_rejects_repository_path(monkeypatch):
    repo_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("SRP_SESSION_DATA_ROOT", str(repo_root / "formal-data"))
    monkeypatch.setenv("SRP_SESSION_WRITER_ACCOUNT", "p02-writer")
    monkeypatch.setenv("SRP_SESSION_WRITER_ROLE", "primary_operator")
    with pytest.raises(StoreError, match="FORMAL_STORAGE_UNAVAILABLE"):
        DurableManifestStore.from_formal_environment(repo_root)


def test_formal_manifest_store_rejects_account_and_environment_checks(
    monkeypatch, tmp_path
):
    import srp_session_store.adapters as adapters

    monkeypatch.setenv("SRP_SESSION_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("SRP_SESSION_WRITER_ACCOUNT", "p02-writer")
    monkeypatch.setenv("SRP_SESSION_WRITER_ROLE", "primary_operator")
    monkeypatch.setattr(adapters, "_system_account", lambda: "wrong-account")
    with pytest.raises(StoreError, match="FORMAL_STORAGE_UNAVAILABLE"):
        DurableManifestStore.from_formal_environment(Path(__file__).resolve().parents[3])

    monkeypatch.setattr(adapters, "_system_account", lambda: "p02-writer")
    monkeypatch.setattr(adapters, "_formal_environment_checks", lambda *_: False)
    with pytest.raises(StoreError, match="FORMAL_STORAGE_UNAVAILABLE"):
        DurableManifestStore.from_formal_environment(Path(__file__).resolve().parents[3])


def test_manifest_storage_failure_prevents_prepare_control(
    tmp_path, manifest_factory, assignment_factory, monkeypatch
):
    import srp_session_store.adapters as adapters

    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)

    def fail_create(*args, **kwargs):
        raise StoreError("STORAGE_APPEND_FAILED")

    monkeypatch.setattr(adapters.SessionArchive, "create", fail_create)
    with pytest.raises(StoreError, match="STORAGE_APPEND_FAILED"):
        core.prepare(manifest, assignment_factory(manifest), 0)
    assert core.snapshot().status.value == "CREATED"
    assert store.archive is None


def test_incomplete_operation_is_not_replayed(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    store.archive.append_l1(
        "operation_begin",
        {
            "arguments": {"now_ns": 5},
            "method": "advance",
            "operation_id": "operation-999999",
        },
        5,
    )
    store.archive.seal({"status": "ABORTED", "reason_code": "TEST"}, 6)
    store.archive.close()
    with pytest.raises(StoreError, match="INCOMPLETE_OPERATION"):
        SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"])).replay_core()


def test_malformed_operation_record_maps_to_stable_store_error(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    store.archive.append_l1("operation_begin", {}, 5)
    store.archive.seal({"status": "ABORTED", "reason_code": "TEST"}, 6)
    store.archive.close()

    with pytest.raises(StoreError, match="REPLAY_RECORD_INVALID"):
        SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"])).replay_core()


def test_commit_before_begin_or_method_mismatch_is_rejected(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    store.archive.append_l1(
        "operation_commit",
        {
            "method": "advance",
            "operation_id": "operation-out-of-order",
            "output": {"output_type": "CoreUpdate"},
        },
        5,
    )
    store.archive.append_l1(
        "operation_begin",
        {
            "arguments": {"now_ns": 5},
            "method": "finish",
            "operation_id": "operation-out-of-order",
        },
        5,
    )
    store.archive.seal({"status": "ABORTED", "reason_code": "TEST"}, 6)
    store.archive.close()

    with pytest.raises(StoreError, match="REPLAY_RECORD_INVALID"):
        SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"])).replay_core()


def test_replay_rejects_core_factory_with_external_dependencies(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    summary = core.finish("TEST_COMPLETE", 1)
    store.archive.seal(summary, 1)
    store.archive.close()

    def unsafe_factory(_safe_dependencies):
        return SessionCore(dependencies=RuntimeDependencies.development())

    replayer = SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"]))
    with pytest.raises(StoreError, match="REPLAY_CORE_UNSAFE"):
        replayer.replay_core(unsafe_factory)


def test_replay_does_not_invoke_mutating_factory(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    summary = core.finish("TEST_COMPLETE", 1)
    store.archive.seal(summary, 1)
    store.archive.close()
    side_effects = []

    def mutating_factory(dependencies):
        side_effects.append("called")
        dependencies.mark_exposed = lambda *_: side_effects.append("exposed")
        return SessionCore(dependencies=dependencies)

    replayer = SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"]))
    with pytest.raises(StoreError, match="REPLAY_CORE_UNSAFE"):
        replayer.replay_core(mutating_factory)
    assert side_effects == []


def test_telemetry_is_stored_before_delegate_publish(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    core.confirm_delivery(
        {
            "schema_version": "2.1",
            "message_type": "ack",
            "session_id": manifest["session_id"],
            "event_id": f"{manifest['session_id']}:control:000001",
            "received_monotonic_ns": 1,
            "applied_monotonic_ns": 2,
            "unity_frame": 1,
            "result": "applied",
            "error_code": None,
        },
        2,
    )
    core.apply_operator_request(OperatorRequest("REQ-START", "start"), 3)

    class Delegate:
        def __init__(self):
            self.core = core

        def publish(self, frame):
            stored = list(ReplayReader.open(tmp_path, manifest["session_id"]).iter_l1("telemetry_frame"))
            assert stored[-1]["payload"]["frame_seq"] == frame["frame_seq"]
            return True

        def close(self):
            pass

    frame = {
        "schema_version": "2.1",
        "message_type": "telemetry_frame",
        "session_id": manifest["session_id"],
        "frame_seq": 1,
        "clock_domain_id": "python:test",
        "source_monotonic_ns": 4,
        "received_monotonic_ns": 4,
        "sent_monotonic_ns": 4,
        "clock_offset_ns": 0,
        "clock_drift_ppm": 0,
        "sync_uncertainty_ns": 0,
        "module_id": "storm",
        "module_position": 0,
        "segment": "demo",
        "target_phase": "inhale",
        "target_progress": 0.1,
        "actual_phase": "inhale",
        "actual_progress": 0.1,
        "actual_confidence": 1.0,
        "recovery_value": 0.0,
        "recovery_locked": False,
        "signal_quality": {"resp": "GOOD", "ecg": "GOOD"},
        "fallback_state": "GOOD",
        "fallback_reason": None,
        "resp_device_state": "CONNECTED",
        "ecg_device_state": "CONNECTED",
        "cue_mode": "scene_native",
        "runtime_mode": "dev_replay",
        "policy_decision_id": "PD-P02-0",
    }
    assert RecordingTelemetryPublisher(Delegate(), store).publish(frame)
    store.archive.close()


def test_abort_control_is_preserved_when_durable_commit_fails(
    tmp_path, manifest_factory, assignment_factory, monkeypatch
):
    manifest = manifest_factory()
    core, store = build_recording_core(tmp_path)
    core.prepare(manifest, assignment_factory(manifest), 0)
    original_append = store.archive.append_l1

    def fail_commit(record_type, payload, now_ns):
        if record_type == "operation_commit":
            raise StoreError("STORAGE_APPEND_FAILED")
        return original_append(record_type, payload, now_ns)

    monkeypatch.setattr(store.archive, "append_l1", fail_commit)
    update = core.apply_operator_request(
        OperatorRequest("REQ-ABORT", "abort", "TEST_ABORT"), 1
    )
    assert update.snapshot.status.value == "ABORTED"
    assert [event["event_type"] for event in update.control_events] == ["abort"]
    store.archive.close()


def test_v22_telemetry_identity_is_preserved_and_replay_is_deterministic(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory(schema_version="2.2")
    core, store = build_recording_core(tmp_path)
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    core.confirm_delivery(
        {
            "schema_version": "2.2",
            "message_type": "ack",
            "session_id": manifest["session_id"],
            "event_id": prepared.control_events[0]["event_id"],
            "received_monotonic_ns": 1,
            "applied_monotonic_ns": 1,
            "unity_frame": 1,
            "result": "applied",
            "error_code": None,
        },
        1,
    )
    core.apply_operator_request(OperatorRequest("REQ-V22-START", "start"), 2)
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "05-通信协议"
        / "contracts"
        / "fixtures-v2.2"
        / "valid"
        / "telemetry-storm-hold-2.json"
    )
    frame = json.loads(fixture_path.read_text(encoding="utf-8"))
    frame.update(
        session_id=manifest["session_id"],
        runtime_mode=manifest["runtime_mode"],
        segment=core.snapshot().segment,
        source_monotonic_ns=3,
        received_monotonic_ns=3,
        sent_monotonic_ns=3,
    )

    class Delegate:
        def __init__(self):
            self.core = core

        def publish(self, frame):
            return frame["schema_version"] == "2.2"

        def close(self):
            pass

    publisher = RecordingTelemetryPublisher(Delegate(), store)
    assert publisher.publish(frame)
    stored = list(ReplayReader.open(tmp_path, manifest["session_id"]).iter_l1("telemetry_frame"))[-1]
    assert {key: stored["payload"][key] for key in (
        "target_cycle_index", "target_step_id", "actual_cycle_index", "actual_step_id"
    )} == {key: frame[key] for key in (
        "target_cycle_index", "target_step_id", "actual_cycle_index", "actual_step_id"
    )}

    unmigrated = dict(frame)
    unmigrated["schema_version"] = "2.1"
    unmigrated["frame_seq"] = frame["frame_seq"] + 1
    for key in (
        "target_cycle_index", "target_step_id", "actual_cycle_index", "actual_step_id"
    ):
        unmigrated.pop(key)
    with pytest.raises(TransportError, match="TELEMETRY_SNAPSHOT_MISMATCH"):
        publisher.publish(unmigrated)

    summary = core.finish("TEST_COMPLETE", 4)
    store.archive.seal(summary, 4)
    store.archive.close()
    assert SessionReplayer(
        ReplayReader.open(tmp_path, manifest["session_id"])
    ).replay_core().valid


def test_v22_pause_resume_frames_fail_closed_and_replay_twice_identically(
    tmp_path, manifest_factory, assignment_factory
):
    manifest = manifest_factory(schema_version="2.2")
    core, store = build_recording_core(tmp_path)
    prepared = core.prepare(manifest, assignment_factory(manifest), 0)
    core.confirm_delivery(
        {
            "schema_version": "2.2",
            "message_type": "ack",
            "session_id": manifest["session_id"],
            "event_id": prepared.control_events[0]["event_id"],
            "received_monotonic_ns": 1,
            "applied_monotonic_ns": 1,
            "unity_frame": 1,
            "result": "applied",
            "error_code": None,
        },
        1,
    )
    core.apply_operator_request(OperatorRequest("REQ-START-22", "start"), 2)

    class Delegate:
        def __init__(self):
            self.core = core

        def publish(self, frame):
            return True

        def close(self):
            pass

    publisher = RecordingTelemetryPublisher(Delegate(), store)

    def frame(seq, now_ns, step_id):
        snapshot = core.snapshot()
        value = {
            "schema_version": "2.2",
            "message_type": "telemetry_frame",
            "session_id": manifest["session_id"],
            "frame_seq": seq,
            "clock_domain_id": "python:S-P01-0001",
            "source_monotonic_ns": now_ns - 2,
            "received_monotonic_ns": now_ns - 1,
            "sent_monotonic_ns": now_ns,
            "clock_offset_ns": 0,
            "clock_drift_ppm": 0.0,
            "sync_uncertainty_ns": 0,
            "module_id": "storm",
            "module_position": 0,
            "segment": snapshot.segment,
            "target_phase": "hold",
            "target_progress": 0.5,
            "target_cycle_index": 0,
            "target_step_id": step_id,
            "actual_phase": "hold",
            "actual_progress": 0.5,
            "actual_confidence": 0.9,
            "actual_cycle_index": 0,
            "actual_step_id": step_id,
            "recovery_value": 0.1,
            "recovery_locked": False,
            "signal_quality": {"resp": 0.9, "ecg": 0.8},
            "fallback_state": "GOOD",
            "fallback_reason": None,
            "resp_device_state": "CONNECTED",
            "ecg_device_state": "CONNECTED",
            "cue_mode": "scene_native",
            "runtime_mode": "dev_replay",
            "policy_decision_id": "PD-P01-0",
        }
        return value

    assert publisher.publish(frame(1, 3, "hold_1"))
    core.apply_operator_request(OperatorRequest("REQ-PAUSE-22", "pause"), 4)
    assert publisher.publish(frame(2, 5, "hold_1"))
    with pytest.raises(TransportError, match="STALE_TELEMETRY_SEQUENCE"):
        publisher.publish(frame(2, 6, "hold_1"))
    invalid_v21 = frame(3, 7, "hold_2")
    invalid_v21["schema_version"] = "2.1"
    for key in ("target_cycle_index", "target_step_id", "actual_cycle_index", "actual_step_id"):
        invalid_v21.pop(key)
    with pytest.raises(TransportError, match="TELEMETRY_SNAPSHOT_MISMATCH"):
        publisher.publish(invalid_v21)
    core.apply_operator_request(OperatorRequest("REQ-RESUME-22", "start"), 8)
    assert publisher.publish(frame(3, 9, "hold_2"))

    stored = list(ReplayReader.open(tmp_path, manifest["session_id"]).iter_l1("telemetry_frame"))
    assert [(item["payload"]["frame_seq"], item["payload"]["target_step_id"]) for item in stored] == [
        (1, "hold_1"),
        (2, "hold_1"),
        (3, "hold_2"),
    ]
    summary = core.finish("TEST_COMPLETE", 10)
    store.archive.seal(summary, 10)
    store.archive.close()
    first = SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"])).replay_core()
    second = SessionReplayer(ReplayReader.open(tmp_path, manifest["session_id"])).replay_core()
    assert first.valid and second.valid
    assert first.expected_final_hash == first.actual_final_hash
    assert second.expected_final_hash == second.actual_final_hash
    assert first.actual_final_hash == second.actual_final_hash
