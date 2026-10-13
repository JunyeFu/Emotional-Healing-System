from __future__ import annotations

from dataclasses import replace
import json
import sqlite3

import pytest

from srp_randomization import (
    AllocationRequest,
    GateEvidence,
    CurrentGateEvidenceVerifier,
    RandomizationError,
    RandomizationStore,
    SnapshotGateEvidenceVerifier,
    generate_list,
)


def _evidence(gate: str, reservation_id: str, *, passed: bool = True) -> GateEvidence:
    return GateEvidence(
        gate=gate,
        reservation_id=reservation_id,
        evidence_id=f"{gate}:PASS",
        passed=passed,
    )


def _request(index: int = 1, *, reservation_id: str = "RES-X01-1") -> AllocationRequest:
    return AllocationRequest(
        request_id=f"REQ-X01-{index}",
        stage="stage_1",
        stratum="all",
        reservation_id=reservation_id,
        expected_randomization_version="1.0",
    )


def _store(tmp_path) -> RandomizationStore:
    store = RandomizationStore(
        tmp_path / "x01.sqlite",
        evidence_verifier=SnapshotGateEvidenceVerifier(),
    )
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"store-test-seed-01"),
        actor_role="custodian",
    )
    return store


def test_reveal_requires_allocator_role_and_all_three_prechecks(tmp_path) -> None:
    store = _store(tmp_path)
    request = _request()
    evidence = (
        _evidence("eligibility", request.reservation_id),
        _evidence("device_readiness", request.reservation_id),
        _evidence("dedup_reservation", request.reservation_id),
    )

    with pytest.raises(RandomizationError, match="UNAUTHORIZED_ROLE"):
        store.allocate_and_reveal(request, evidence, actor_role="auditor")
    with pytest.raises(RandomizationError, match="REQUIRED_GATE_MISSING"):
        store.allocate_and_reveal(request, evidence[:2], actor_role="allocator")
    with pytest.raises(RandomizationError, match="GATE_REJECTED"):
        store.allocate_and_reveal(
            request,
            (*evidence[:2], replace(evidence[2], passed=False)),
            actor_role="allocator",
        )
    with pytest.raises(RandomizationError, match="GATE_EVIDENCE_DUPLICATED"):
        store.allocate_and_reveal(
            request,
            (*evidence, evidence[0]),
            actor_role="allocator",
        )

    receipt = store.allocate_and_reveal(request, evidence, actor_role="allocator")
    assert receipt.reservation_id == request.reservation_id
    assert receipt.arm in {"scene_native", "abstract_pacer"}
    assert receipt.weather_sequence is not None
    assert receipt.arm_behavior_probability == 0.5
    assert len(receipt.policy_decisions("S-X01-0001", 100)) == 4
    with sqlite3.connect(store.database_path) as connection:
        refs = json.loads(
            connection.execute(
                "SELECT evidence_refs_json FROM audit_events "
                "WHERE event_type='ASSIGNMENT_REVEALED'"
            ).fetchone()[0]
        )
    gates = ("eligibility", "device_readiness", "dedup_reservation")
    assert {gate: refs[gate] for gate in gates} == {
        item.gate: item.evidence_id for item in evidence
    }
    assert refs["allocation_binding"].startswith("BIND-")


def test_same_request_is_idempotent_but_reservation_cannot_receive_twice(tmp_path) -> None:
    store = _store(tmp_path)
    request = _request()
    evidence = tuple(
        _evidence(gate, request.reservation_id)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )
    first = store.allocate_and_reveal(request, evidence, actor_role="allocator")
    repeated = store.allocate_and_reveal(request, evidence, actor_role="allocator")

    assert first == repeated
    assert store.verify_audit_chain(actor_role="auditor").valid is True
    with pytest.raises(RandomizationError, match="RESERVATION_ALREADY_ALLOCATED"):
        store.allocate_and_reveal(
            replace(request, request_id="REQ-X01-DIFFERENT"),
            evidence,
            actor_role="allocator",
        )


@pytest.mark.parametrize("field", ["stage", "stratum", "expected_randomization_version"])
def test_idempotent_replay_requires_the_complete_original_request(tmp_path, field) -> None:
    store = _store(tmp_path)
    request = _request()
    evidence = tuple(
        _evidence(gate, request.reservation_id)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )
    store.allocate_and_reveal(request, evidence, actor_role="allocator")
    replacements = {
        "stage": "stage_3",
        "stratum": "other",
        "expected_randomization_version": "9.9",
    }
    with pytest.raises(RandomizationError, match="REQUEST_ID_CONFLICT"):
        store.allocate_and_reveal(
            replace(request, **{field: replacements[field]}),
            evidence,
            actor_role="allocator",
        )


def test_new_reveal_requires_current_gate_state_and_strict_boolean(tmp_path) -> None:
    current = {gate: True for gate in ("eligibility", "device_readiness", "dedup_reservation")}
    verifier = CurrentGateEvidenceVerifier(
        {gate: (lambda _request, _evidence, gate=gate: current[gate]) for gate in current},
        formal_capable=True,
    )
    store = RandomizationStore(
        tmp_path / "x01.sqlite", evidence_verifier=verifier, formal_capable=True
    )
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"current-gate-seed-01"),
        actor_role="custodian",
    )
    request = _request()
    evidence = tuple(
        _evidence(gate, request.reservation_id)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )
    current["dedup_reservation"] = False
    with pytest.raises(RandomizationError, match="GATE_NO_LONGER_VALID"):
        store.allocate_and_reveal(request, evidence, actor_role="allocator")
    with pytest.raises(RandomizationError, match="GATE_REJECTED"):
        store.allocate_and_reveal(
            request,
            (*evidence[:2], replace(evidence[2], passed="false")),  # type: ignore[arg-type]
            actor_role="allocator",
        )


def test_allocation_uses_assigned_rows_not_completion_outcomes(tmp_path) -> None:
    store = _store(tmp_path)
    allocations = []
    for index in range(1, 49):
        request = _request(index, reservation_id=f"RES-X01-{index}")
        evidence = tuple(
            _evidence(gate, request.reservation_id)
            for gate in ("eligibility", "device_readiness", "dedup_reservation")
        )
        allocation = store.allocate_and_reveal(request, evidence, actor_role="allocator")
        allocations.append(allocation)
        if index % 3 == 0:
            store.record_outcome(
                allocation.randomization_list_hash,
                allocation.allocation_index,
                "INCOMPLETE",
                actor_role="auditor",
            )
        else:
            store.record_outcome(
                allocation.randomization_list_hash,
                allocation.allocation_index,
                "COMPLETE",
                actor_role="auditor",
            )

    audit = store.audit_balance("stage_1", "all", actor_role="auditor")
    assert audit.assigned_count == 48
    assert audit.complete_count == 32
    assert audit.balanced_by_assignment is True

    request = _request(49, reservation_id="RES-X01-49")
    evidence = tuple(
        _evidence(gate, request.reservation_id)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )
    with pytest.raises(RandomizationError, match="LIST_EXHAUSTED"):
        store.allocate_and_reveal(request, evidence, actor_role="allocator")


def test_formal_capability_requires_strict_true_from_both_parties(tmp_path) -> None:
    verifier = CurrentGateEvidenceVerifier(
        {
            gate: (lambda _request, _evidence: True)
            for gate in ("eligibility", "device_readiness", "dedup_reservation")
        },
        formal_capable="false",  # type: ignore[arg-type]
    )
    store = RandomizationStore(
        tmp_path / "x01.sqlite",
        evidence_verifier=verifier,
        formal_capable="false",  # type: ignore[arg-type]
    )
    assert store.formal_capable is False
