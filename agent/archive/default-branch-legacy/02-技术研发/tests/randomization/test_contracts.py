from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import jsonschema

from srp_randomization import generate_list


ROOT = Path(__file__).resolve().parents[2] / "08-随机化"


def test_generated_lists_match_machine_schema() -> None:
    schema = json.loads(
        (ROOT / "contracts/randomization-list-v1.schema.json").read_text(encoding="utf-8")
    )
    for stage in ("stage_1", "stage_3"):
        plan = generate_list(stage, ("all",), 1, f"contract-seed-{stage}".encode())
        jsonschema.Draft202012Validator(schema).validate(plan.to_dict())


def test_allocation_receipt_matches_machine_schema(tmp_path) -> None:
    from srp_randomization import (
        AllocationRequest,
        GateEvidence,
        RandomizationStore,
        SnapshotGateEvidenceVerifier,
    )

    schema = json.loads(
        (ROOT / "contracts/allocation-receipt-v1.schema.json").read_text(encoding="utf-8")
    )
    store = RandomizationStore(
        tmp_path / "contract.sqlite",
        evidence_verifier=SnapshotGateEvidenceVerifier(),
    )
    store.import_list(
        generate_list("stage_1", ("all",), 1, b"receipt-contract-seed"),
        actor_role="custodian",
    )
    reservation = "RES-CONTRACT"
    receipt = store.allocate_and_reveal(
        AllocationRequest("REQ-CONTRACT", "stage_1", "all", reservation, "1.0"),
        tuple(
            GateEvidence(gate, reservation, f"{gate}:PASS", True)
            for gate in ("eligibility", "device_readiness", "dedup_reservation")
        ),
        actor_role="allocator",
    )
    payload = asdict(receipt)
    payload["weather_sequence"] = list(receipt.weather_sequence or ())
    jsonschema.Draft202012Validator(schema).validate(payload)
