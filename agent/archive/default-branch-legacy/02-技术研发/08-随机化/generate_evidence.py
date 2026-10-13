from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from itertools import permutations
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent
TECH_ROOT = ROOT.parent
for path in (ROOT, TECH_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from srp_randomization import (  # noqa: E402
    AllocationRequest,
    GateEvidence,
    RandomizationStore,
    SnapshotGateEvidenceVerifier,
    generate_list,
    policy_decisions,
)
from srp_session_core.contract_adapter import validate_message  # noqa: E402


STRATA = ("synthetic_stratum_a", "synthetic_stratum_b")
WEATHERS = ("storm", "heat", "snow", "fade")


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write("\n")


def _gate_evidence(reservation_id: str) -> tuple[GateEvidence, ...]:
    return tuple(
        GateEvidence(gate, reservation_id, f"{gate}:SYNTHETIC_PASS", True)
        for gate in ("eligibility", "device_readiness", "dedup_reservation")
    )


def main() -> int:
    stage_1 = generate_list("stage_1", STRATA, 2, b"x01-synthetic-stage-1-seed")
    stage_3 = generate_list("stage_3", STRATA, 2, b"x01-synthetic-stage-3-seed")
    _write(ROOT / "fixtures/synthetic/stage_1_list_v1.json", stage_1.to_dict())
    _write(ROOT / "fixtures/synthetic/stage_3_list_v1.json", stage_3.to_dict())

    probability_vectors = set()
    for index, sequence in enumerate(permutations(WEATHERS)):
        decisions = policy_decisions(
            session_id=f"S-X01-SYNTHETIC-{index:02d}",
            stage="stage_1",
            sequence=sequence,
            created_monotonic_ns=index,
        )
        for decision in decisions:
            validate_message("policy_decision", decision)
        probability_vectors.add(tuple(item["behavior_probability"] for item in decisions))
    probability_report = {
        "evidence_status": "SYNTHETIC_ONLY",
        "randomization_version": "1.0",
        "checked_sequences": 24,
        "unique_probability_vectors": [list(item) for item in sorted(probability_vectors)],
        "expected_probability_vector": [0.25, 1 / 3, 0.5, 1.0],
        "contract_validation": "PASS",
    }
    _write(ROOT / "evidence/probability_report_v1.json", probability_report)

    with TemporaryDirectory(prefix="srp-x01-") as temporary:
        store = RandomizationStore(
            Path(temporary) / "x01.sqlite",
            evidence_verifier=SnapshotGateEvidenceVerifier(),
        )
        store.import_list(stage_1, actor_role="custodian")
        for stratum in STRATA:
            for index in range(96):
                reservation = f"RES-{stratum}-{index:03d}"
                receipt = store.allocate_and_reveal(
                    AllocationRequest(
                        request_id=f"REQ-{stratum}-{index:03d}",
                        stage="stage_1",
                        stratum=stratum,
                        reservation_id=reservation,
                        expected_randomization_version="1.0",
                    ),
                    _gate_evidence(reservation),
                    actor_role="allocator",
                )
                outcome = "INCOMPLETE" if index % 5 == 0 else "COMPLETE"
                store.record_outcome(
                    receipt.randomization_list_hash,
                    receipt.allocation_index,
                    outcome,
                    actor_role="auditor",
                )
        balance = [asdict(store.audit_balance("stage_1", item, actor_role="auditor")) for item in STRATA]
        _write(
            ROOT / "evidence/balance_report_v1.json",
            {
                "evidence_status": "SYNTHETIC_ONLY",
                "balance_basis": "assigned",
                "strata": balance,
            },
        )

    with TemporaryDirectory(prefix="srp-x01-duplicate-") as temporary:
        store = RandomizationStore(
            Path(temporary) / "x01.sqlite",
            evidence_verifier=SnapshotGateEvidenceVerifier(),
        )
        one_block = generate_list("stage_1", ("synthetic",), 1, b"x01-duplicate-fixture-seed")
        store.import_list(one_block, actor_role="custodian")
        request = AllocationRequest("REQ-DUP", "stage_1", "synthetic", "RES-DUP", "1.0")
        first = store.allocate_and_reveal(
            request, _gate_evidence("RES-DUP"), actor_role="allocator"
        )
        repeated = store.allocate_and_reveal(
            request, _gate_evidence("RES-DUP"), actor_role="allocator"
        )
        audit = store.verify_audit_chain(actor_role="auditor")
        duplicate_report = {
            "evidence_status": "SYNTHETIC_ONLY",
            "same_allocation": first == repeated,
            "allocation_index": first.allocation_index,
            "audit": asdict(audit),
            "expected_conflict_code_for_new_request_same_reservation": "RESERVATION_ALREADY_ALLOCATED",
        }
        _write(ROOT / "fixtures/synthetic/duplicate_audit_fixture_v1.json", duplicate_report)

    stage_1_arms = Counter(record.arm for record in stage_1.records)
    stage_3_arms = Counter(record.arm for record in stage_3.records)
    _write(
        ROOT / "evidence/x01_validation_report_v1.json",
        {
            "evidence_status": "SYNTHETIC_ONLY",
            "stage_1": {
                "list_hash": stage_1.list_hash,
                "record_count": len(stage_1.records),
                "arm_counts": dict(stage_1_arms),
                "complete_blocks": 4,
            },
            "stage_3": {
                "list_hash": stage_3.list_hash,
                "record_count": len(stage_3.records),
                "arm_counts": dict(stage_3_arms),
                "complete_blocks": 4,
            },
            "formal_strata_and_cutpoints": "PENDING_PREREGISTRATION",
            "formal_machine_and_acl": "G-05_OPEN",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
