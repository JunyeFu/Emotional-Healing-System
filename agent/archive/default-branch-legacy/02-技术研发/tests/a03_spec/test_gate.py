from __future__ import annotations

import json
from pathlib import Path

from a03_gate2_spec import GateEvidence, GateResult, evaluate_ordered_gate


ALL_PASS = GateEvidence(*([GateResult.PASS] * 6))
SYNTHETIC_FIXTURE_RECEIPT = {
    "evidence_class": "SYNTHETIC_ONLY",
    "status": "FIXTURE",
    "config_sha256": "A" * 64,
}


def test_gate_requires_a03_cal_before_formal_evaluation():
    result = evaluate_ordered_gate(ALL_PASS)
    assert result["result"] == "NOT_EVALUABLE"
    assert result["reason_code"] == "A03_CAL_NOT_DONE"


def test_gate_stops_at_first_failure_without_compensation():
    evidence = GateEvidence(
        GateResult.PASS,
        GateResult.FAIL,
        GateResult.PASS,
        GateResult.PASS,
        GateResult.PASS,
        GateResult.PASS,
    )
    result = evaluate_ordered_gate(
        evidence,
        evaluation_mode="synthetic_fixture",
        fixture_receipt=SYNTHETIC_FIXTURE_RECEIPT,
    )
    assert result["result"] == "FAIL"
    assert result["stopped_at"] == "scci_direction"


def test_gate_passes_only_when_every_component_passes():
    result = evaluate_ordered_gate(
        ALL_PASS,
        evaluation_mode="synthetic_fixture",
        fixture_receipt=SYNTHETIC_FIXTURE_RECEIPT,
    )
    assert result["result"] == "PASS"


def test_freeze_reason_fixture_covers_missing_and_candidate_cases():
    fixture = Path(__file__).resolve().parents[2] / "02-信号处理" / "a03_gate2_spec" / "fixtures" / "scoring_edge_cases_v1.0.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))["freeze_cases"]
    observed = [
        evaluate_ordered_gate(
            ALL_PASS,
            evaluation_mode=case["evaluation_mode"],
            fixture_receipt=case.get("fixture_receipt"),
        )["reason_code"]
        for case in cases
    ]
    assert observed == [case["expected"] for case in cases]


def test_arbitrary_strings_cannot_unlock_formal_gate():
    result = evaluate_ordered_gate(
        ALL_PASS,
        evaluation_mode="formal",
        fixture_receipt={"noninferiority_margins": "x"},
    )
    assert result["result"] == "NOT_EVALUABLE"
    assert result["reason_code"] == "A03_CAL_NOT_DONE"


def test_synthetic_receipt_rejects_bad_hash_and_unknown_fields():
    for receipt in (
        {"evidence_class": "SYNTHETIC_ONLY", "status": "FIXTURE", "config_sha256": "x"},
        {**SYNTHETIC_FIXTURE_RECEIPT, "unknown": True},
        {**SYNTHETIC_FIXTURE_RECEIPT, "status": "SIGNED"},
    ):
        result = evaluate_ordered_gate(
            ALL_PASS,
            evaluation_mode="synthetic_fixture",
            fixture_receipt=receipt,
        )
        assert result["reason_code"] == "SYNTHETIC_FIXTURE_RECEIPT_INVALID"
