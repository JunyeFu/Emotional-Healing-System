from __future__ import annotations

from dataclasses import replace

import pytest

from srp_randomization import (
    AllocationRequest,
    GateEvidence,
    RandomizationError,
    RandomizationStore,
    CurrentGateEvidenceVerifier,
    X01AssignmentGate,
    generate_list,
)
from srp_session_core import AssignmentBundle
from srp_session_core.errors import SessionCoreError


def test_p01_gate_accepts_exact_revealed_assignment_and_rejects_drift(tmp_path) -> None:
    verifier = CurrentGateEvidenceVerifier(
        {
            gate: (lambda _request, _evidence: True)
            for gate in ("eligibility", "device_readiness", "dedup_reservation")
        },
        formal_capable=True,
    )
    store = RandomizationStore(
        tmp_path / "x01.sqlite", evidence_verifier=verifier, formal_capable=True
    )
    plan = generate_list("stage_1", ("all",), 1, b"gate-test-seed-01")
    store.import_list(plan, actor_role="custodian")
    request = AllocationRequest("REQ-1", "stage_1", "all", "RES-1", "1.0")
    evidence = tuple(
        GateEvidence(gate, "RES-1", f"{gate}:PASS", True)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )
    receipt = store.allocate_and_reveal(request, evidence, actor_role="allocator")
    decisions = receipt.policy_decisions("S-X01-GATE", 0)
    assignment = receipt.to_assignment_bundle("S-X01-GATE", 0)
    manifest = {
        "session_id": "S-X01-GATE",
        "study_stage": "stage_1",
        "runtime_mode": "formal_stage_1",
        "cue_mode": receipt.arm,
        "assignment_arm": receipt.arm,
        "allocation_index": receipt.allocation_index,
        "randomization_stratum": receipt.stratum,
        "randomization_block": receipt.block,
        "randomization_list_hash": receipt.randomization_list_hash,
        "randomization_version": "1.0",
        "weather_sequence": list(receipt.weather_sequence or ()),
    }
    gate = X01AssignmentGate(store)

    accepted = gate.check(manifest, assignment, "sha256:config")
    assert accepted.gate == "assignment"
    assert accepted.formal_capable is True
    assert "RES-1" not in accepted.evidence_id

    with pytest.raises(SessionCoreError, match="ASSIGNMENT_LIST_HASH_MISMATCH"):
        gate.check(
            {**manifest, "randomization_list_hash": "sha256:wrong"},
            replace(assignment, randomization_list_hash="sha256:wrong"),
            "sha256:config",
        )


def test_p01_gate_converts_store_failures_to_session_core_error(tmp_path) -> None:
    verifier = CurrentGateEvidenceVerifier(
        {
            gate: (lambda _request, _evidence: True)
            for gate in ("eligibility", "device_readiness", "dedup_reservation")
        }
    )
    database = tmp_path / "not-a-database"
    database.mkdir()
    store = RandomizationStore(database, evidence_verifier=verifier)
    gate = X01AssignmentGate(store)
    assignment = AssignmentBundle(1, "sha256:missing", ("storm", "heat", "snow", "fade"))
    with pytest.raises(SessionCoreError, match="STORE_UNAVAILABLE"):
        gate.check(
            {"randomization_list_hash": "sha256:missing", "allocation_index": 1},
            assignment,
            "sha256:config",
        )
