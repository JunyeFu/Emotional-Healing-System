from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import jsonschema


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from srp_randomization import load_plan  # noqa: E402


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _forbidden_keys(payload: object) -> set[str]:
    forbidden = {"phone", "email", "hmac", "subject_token", "contact"}
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in forbidden:
                found.add(key)
            found.update(_forbidden_keys(value))
    elif isinstance(payload, list):
        for value in payload:
            found.update(_forbidden_keys(value))
    return found


def verify(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    list_schema = _read(root / "contracts/randomization-list-v1.schema.json")
    raw_plans = {
        stage: _read(root / f"fixtures/synthetic/{stage}_list_v1.json")
        for stage in ("stage_1", "stage_3")
    }
    plans = {
        stage: load_plan(root / f"fixtures/synthetic/{stage}_list_v1.json")
        for stage in raw_plans
    }
    for stage, plan in plans.items():
        try:
            jsonschema.Draft202012Validator(list_schema).validate(raw_plans[stage])
        except jsonschema.ValidationError as error:
            errors.append(f"{stage}:SCHEMA:{error.json_path}")
        if plan.stage != stage or len(plan.records) != 192:
            errors.append(f"{stage}:SHAPE")
        if _forbidden_keys(raw_plans[stage]):
            errors.append(f"{stage}:FORBIDDEN_KEYS")

    stage_1_counts = Counter(record.arm for record in plans["stage_1"].records)
    stage_3_counts = Counter(record.arm for record in plans["stage_3"].records)
    if stage_1_counts != {"scene_native": 96, "abstract_pacer": 96}:
        errors.append("stage_1:ARM_COUNTS")
    if stage_3_counts != {"frozen_policy": 96, "balanced_random": 96}:
        errors.append("stage_3:ARM_COUNTS")

    probability = _read(root / "evidence/probability_report_v1.json")
    expected_vector = [0.25, 1 / 3, 0.5, 1.0]
    if probability != {
        "evidence_status": "SYNTHETIC_ONLY",
        "randomization_version": "1.0",
        "checked_sequences": 24,
        "unique_probability_vectors": [expected_vector],
        "expected_probability_vector": expected_vector,
        "contract_validation": "PASS",
    }:
        errors.append("PROBABILITY_REPORT")
    stage_1_by_stratum: dict[str, list[object]] = {}
    for record in plans["stage_1"].records:
        stage_1_by_stratum.setdefault(record.stratum, []).append(record)
    expected_strata = []
    for stratum, records in sorted(stage_1_by_stratum.items()):
        assigned_count = len(records)
        incomplete_count = sum(1 for index in range(assigned_count) if index % 5 == 0)
        arm_counts = dict(Counter(record.arm for record in records))
        expected_strata.append(
            {
                "stage": "stage_1",
                "stratum": stratum,
                "assigned_count": assigned_count,
                "complete_count": assigned_count - incomplete_count,
                "incomplete_count": incomplete_count,
                "arm_counts": arm_counts,
                "balanced_by_assignment": len(set(arm_counts.values())) == 1,
                "reason_code": "BALANCED_BY_ASSIGNMENT",
            }
        )
    balance = _read(root / "evidence/balance_report_v1.json")
    if balance != {
        "evidence_status": "SYNTHETIC_ONLY",
        "balance_basis": "assigned",
        "strata": expected_strata,
    }:
        errors.append("BALANCE_REPORT")
    duplicate = _read(root / "fixtures/synthetic/duplicate_audit_fixture_v1.json")
    if duplicate != {
        "evidence_status": "SYNTHETIC_ONLY",
        "same_allocation": True,
        "allocation_index": 1,
        "audit": {
            "valid": True,
            "checked_events": 3,
            "reason_code": "AUDIT_CHAIN_VALID",
        },
        "expected_conflict_code_for_new_request_same_reservation": "RESERVATION_ALREADY_ALLOCATED",
    }:
        errors.append("DUPLICATE_AUDIT")
    summary = _read(root / "evidence/x01_validation_report_v1.json")
    expected_summary: dict[str, object] = {
        "evidence_status": "SYNTHETIC_ONLY",
        "formal_strata_and_cutpoints": "PENDING_PREREGISTRATION",
        "formal_machine_and_acl": "G-05_OPEN",
    }
    for stage, plan in plans.items():
        expected_summary[stage] = {
            "list_hash": plan.list_hash,
            "record_count": len(plan.records),
            "arm_counts": dict(Counter(record.arm for record in plan.records)),
            "complete_blocks": len(
                {(record.stratum, record.block) for record in plan.records}
            ),
        }
    if summary != expected_summary:
        errors.append("SUMMARY_REPORT")
    return errors


def main() -> int:
    errors = verify()
    if errors:
        print("X01_VERIFY_FAIL " + ",".join(errors))
        return 1
    print("X01_VERIFY_PASS lists=2 records=384 stage1=192 stage3=192")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
