from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest

from srp_randomization import (
    AllocationRequest,
    GateEvidence,
    RandomizationError,
    RandomizationStore,
    SnapshotGateEvidenceVerifier,
    gate_evidence_from_dedup,
    generate_list,
    load_plan,
    verify_plan,
    write_plan,
)


def _evidence(reservation_id: str) -> tuple[GateEvidence, ...]:
    return tuple(
        GateEvidence(gate, reservation_id, f"{gate}:PASS", True)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )


def test_sealed_file_round_trip_and_tamper_detection(tmp_path) -> None:
    plan = generate_list("stage_1", ("all",), 1, b"sealed-plan-seed-01")
    path = tmp_path / "list.json"
    write_plan(plan, path)
    assert load_plan(path) == plan
    with pytest.raises(RandomizationError, match="LIST_FILE_ALREADY_EXISTS"):
        write_plan(plan, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["arm"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RandomizationError, match="LIST_FILE_INVALID"):
        load_plan(path)


def test_recomputed_hash_cannot_hide_invalid_arm_probability() -> None:
    plan = generate_list("stage_1", ("all",), 1, b"invalid-plan-seed")
    invalid = replace(
        plan,
        records=(replace(plan.records[0], arm_behavior_probability=0.75), *plan.records[1:]),
    )
    encoded = json.dumps(
        invalid.unsigned_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    invalid = replace(invalid, list_hash=f"sha256:{hashlib.sha256(encoded).hexdigest()}")
    with pytest.raises(RandomizationError, match="ARM_PROBABILITY_INVALID"):
        verify_plan(invalid)


def test_two_concurrent_requests_receive_distinct_rows(tmp_path) -> None:
    store = RandomizationStore(
        tmp_path / "concurrent.sqlite",
        evidence_verifier=SnapshotGateEvidenceVerifier(),
    )
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"concurrent-seed-01"),
        actor_role="custodian",
    )

    def allocate(index: int):
        reservation_id = f"RES-{index}"
        return store.allocate_and_reveal(
            AllocationRequest(f"REQ-{index}", "stage_1", "all", reservation_id, "1.0"),
            _evidence(reservation_id),
            actor_role="allocator",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = list(executor.map(allocate, (1, 2)))
    assert len({receipt.allocation_index for receipt in receipts}) == 2


def test_audit_tail_deletion_is_detected(tmp_path) -> None:
    database = tmp_path / "audit.sqlite"
    store = RandomizationStore(database, evidence_verifier=SnapshotGateEvidenceVerifier())
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"audit-chain-seed-01"),
        actor_role="custodian",
    )
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM audit_events")
    report = store.verify_audit_chain(actor_role="auditor")
    assert report.valid is False
    assert report.reason_code == "AUDIT_ANCHOR_MISMATCH"


def test_stored_list_tamper_blocks_reveal(tmp_path) -> None:
    database = tmp_path / "tampered.sqlite"
    store = RandomizationStore(database, evidence_verifier=SnapshotGateEvidenceVerifier())
    plan = generate_list("stage_1", ("all",), 1, b"stored-tamper-seed-01")
    store.import_list(plan, actor_role="custodian")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE allocation_records SET arm = 'tampered' WHERE allocation_index = 1"
        )
    with pytest.raises(RandomizationError, match="LIST_HASH_MISMATCH"):
        store.allocate_and_reveal(
            AllocationRequest("REQ-T", "stage_1", "all", "RES-T", "1.0"),
            _evidence("RES-T"),
            actor_role="allocator",
        )


def test_idempotent_replay_rechecks_the_stored_list(tmp_path) -> None:
    database = tmp_path / "idempotent-tamper.sqlite"
    store = RandomizationStore(database, evidence_verifier=SnapshotGateEvidenceVerifier())
    plan = generate_list("stage_1", ("all",), 1, b"idempotent-tamper-seed-01")
    store.import_list(plan, actor_role="custodian")
    request = AllocationRequest("REQ-T", "stage_1", "all", "RES-T", "1.0")
    store.allocate_and_reveal(request, _evidence("RES-T"), actor_role="allocator")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE allocation_records SET arm = 'tampered' WHERE allocation_index = 2"
        )
    with pytest.raises(RandomizationError, match="LIST_HASH_MISMATCH"):
        store.allocate_and_reveal(request, _evidence("RES-T"), actor_role="allocator")


def test_unknown_fields_are_rejected_before_plan_reconstruction(tmp_path) -> None:
    plan = generate_list("stage_1", ("all",), 1, b"unknown-field-seed-01")
    path = tmp_path / "list.json"
    payload = plan.to_dict()
    payload["email"] = "must-not-be-ignored@example.invalid"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RandomizationError, match="LIST_FILE_INVALID"):
        load_plan(path)

    payload = plan.to_dict()
    payload["records"][0]["subject_token"] = "must-not-be-ignored"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RandomizationError, match="LIST_FILE_INVALID"):
        load_plan(path)


def test_assignment_state_tamper_and_internal_audit_tamper_block_reveal(tmp_path) -> None:
    database = tmp_path / "state-audit.sqlite"
    store = RandomizationStore(database, evidence_verifier=SnapshotGateEvidenceVerifier())
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"state-audit-seed-01"),
        actor_role="custodian",
    )
    first_request = AllocationRequest("REQ-1", "stage_1", "all", "RES-1", "1.0")
    store.allocate_and_reveal(first_request, _evidence("RES-1"), actor_role="allocator")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE allocation_records SET request_id=NULL, reservation_id=NULL, "
            "permit_id=NULL, assigned_at_utc=NULL WHERE allocation_index=1"
        )
    with pytest.raises(RandomizationError, match="ALLOCATION_AUDIT_MISMATCH"):
        store.allocate_and_reveal(
            AllocationRequest("REQ-2", "stage_1", "all", "RES-2", "1.0"),
            _evidence("RES-2"),
            actor_role="allocator",
        )

    database2 = tmp_path / "internal-audit.sqlite"
    store2 = RandomizationStore(database2, evidence_verifier=SnapshotGateEvidenceVerifier())
    store2.import_list(
        generate_list("stage_1", ("all",), 1, b"internal-audit-seed-01"),
        actor_role="custodian",
    )
    with sqlite3.connect(database2) as connection:
        connection.execute("UPDATE audit_events SET reason_code='TAMPERED' WHERE sequence=1")
    with pytest.raises(RandomizationError, match="AUDIT_CHAIN_INVALID"):
        store2.allocate_and_reveal(
            AllocationRequest("REQ-3", "stage_1", "all", "RES-3", "1.0"),
            _evidence("RES-3"),
            actor_role="allocator",
        )


def test_reservation_tamper_is_bound_to_the_reveal_audit(tmp_path) -> None:
    database = tmp_path / "reservation-audit.sqlite"
    store = RandomizationStore(database, evidence_verifier=SnapshotGateEvidenceVerifier())
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"reservation-audit-seed-01"),
        actor_role="custodian",
    )
    store.allocate_and_reveal(
        AllocationRequest("REQ-1", "stage_1", "all", "RES-1", "1.0"),
        _evidence("RES-1"),
        actor_role="allocator",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE allocation_records SET reservation_id='RES-CHANGED' "
            "WHERE request_id='REQ-1'"
        )
    assert store.verify_audit_chain(actor_role="auditor").reason_code == (
        "ALLOCATION_AUDIT_MISMATCH"
    )


def test_balance_audit_rejects_unlogged_assignment_state(tmp_path) -> None:
    database = tmp_path / "balance-audit.sqlite"
    store = RandomizationStore(database, evidence_verifier=SnapshotGateEvidenceVerifier())
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"balance-audit-seed-01"),
        actor_role="custodian",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE allocation_records SET request_id='REQ-FAKE', "
            "reservation_id='RES-FAKE', permit_id='PERMIT-FAKE', "
            "assigned_at_utc='2026-09-06T00:00:00Z' WHERE allocation_index=1"
        )
    with pytest.raises(RandomizationError, match="ALLOCATION_AUDIT_MISMATCH"):
        store.audit_balance("stage_1", "all", actor_role="auditor")


def test_read_side_integrity_checks_run_inside_one_sqlite_snapshot(
    tmp_path, monkeypatch
) -> None:
    store = RandomizationStore(
        tmp_path / "read-snapshot.sqlite",
        evidence_verifier=SnapshotGateEvidenceVerifier(),
    )
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"read-snapshot-seed-01"),
        actor_role="custodian",
    )
    request = AllocationRequest("REQ-1", "stage_1", "all", "RES-1", "1.0")
    receipt = store.allocate_and_reveal(
        request, _evidence("RES-1"), actor_role="allocator"
    )
    observed: list[bool] = []
    original = RandomizationStore._audit_integrity

    def require_transaction(connection):
        observed.append(connection.in_transaction)
        return original(connection)

    monkeypatch.setattr(
        RandomizationStore, "_audit_integrity", staticmethod(require_transaction)
    )
    store.verify_audit_chain(actor_role="auditor")
    store.audit_balance("stage_1", "all", actor_role="auditor")
    store.validate_assignment(
        {
            "randomization_list_hash": receipt.randomization_list_hash,
            "allocation_index": receipt.allocation_index,
            "study_stage": receipt.stage,
            "randomization_stratum": receipt.stratum,
            "randomization_block": receipt.block,
            "assignment_arm": receipt.arm,
            "cue_mode": receipt.arm,
            "randomization_version": receipt.randomization_version,
            "weather_sequence": list(receipt.weather_sequence or ()),
        },
        receipt.to_assignment_bundle("S-X01-SNAPSHOT", 0),
    )
    assert observed == [True, True, True]


def test_g02_adapter_exports_only_opaque_receipt_fields() -> None:
    evidence = gate_evidence_from_dedup(
        SimpleNamespace(
            allowed=True,
            reservation_id="RES-G02-1",
            audit_event_id="AUD-G02-1",
            token_version=1,
        )
    )
    assert evidence == GateEvidence(
        "dedup_reservation", "RES-G02-1", "AUD-G02-1", True
    )
    assert set(evidence.__dict__) == {"gate", "reservation_id", "evidence_id", "passed"}
