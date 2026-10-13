from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
ESTIMANDS = (
    ROOT
    / "00-项目管理"
    / "01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
    / "22_离线处理与科研分析"
    / "A-03_SPEC"
    / "estimands_v1.0.json"
)


def test_gate1_to_gate3_estimands_are_complete_and_ordered():
    document = json.loads(ESTIMANDS.read_text(encoding="utf-8"))
    gates = {gate["gate_id"]: gate for gate in document["gates"]}
    assert list(gates) == [
        "GATE1_PROTOCOL_FIDELITY",
        "GATE2_REPRESENTATION_AND_FUNCTION",
        "GATE3_SEQUENCE_EXTENSION",
    ]
    assert gates["GATE1_PROTOCOL_FIDELITY"]["analysis_sets"] == [
        "FULL_ANALYSIS_SET", "COMPLETE_FOUR_MODULE_SET"
    ]
    assert gates["GATE1_PROTOCOL_FIDELITY"]["decision_rule"] == (
        "BOTH_ANALYSIS_SETS_CI95_LOWER_GT_NEGATIVE_0_075"
    )
    assert gates["GATE2_REPRESENTATION_AND_FUNCTION"]["prerequisite"] == "GATE1_PASS"
    assert gates["GATE2_REPRESENTATION_AND_FUNCTION"]["formal_parameters"] == (
        "PENDING_LEVEL_B_AND_BLIND_CALIBRATION"
    )
    assert gates["GATE3_SEQUENCE_EXTENSION"]["conditions"] == [
        "frozen_policy", "balanced_random"
    ]
    assert gates["GATE3_SEQUENCE_EXTENSION"]["status"] == "CONDITIONAL_EXTENSION"
    assert document["formal_sample_size"] is None
