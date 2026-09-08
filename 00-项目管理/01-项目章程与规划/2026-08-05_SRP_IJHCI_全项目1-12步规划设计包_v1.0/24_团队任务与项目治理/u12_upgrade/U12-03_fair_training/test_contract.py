import copy
import json
import runpy
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
V = runpy.run_path(str(HERE / "validate.py"))


def inputs():
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))
    return read(HERE / "contract.json"), read(V["BREATH"]), read(HERE / "observation.template.json")


def test_candidate():
    assert V["validate"](*inputs()) == []


@pytest.mark.parametrize("key,value,code", [
    ("formal_collection_allowed", True, "UNAPPROVED_FREEZE"),
    ("formal_training_budget_seconds", 180, "UNAPPROVED_FREEZE"),
    ("native_is_hidden", True, "CONDITION_DEFINITION"),
    ("arm_budget_seconds", {"scene_native": 200, "abstract_pacer": 180}, "BUDGET_MISMATCH"),
    ("candidate_budget_seconds", 179, "BUDGET_MISMATCH"),
    ("weather_order", "performance", "ASSIGNMENT_ORDER"),
    ("mastery_based_extension", True, "ADAPTIVE_TRAINING_OR_SELECTION"),
    ("exclude_for_slow_learning", True, "ADAPTIVE_TRAINING_OR_SELECTION"),
    ("extra_instruction_repetitions", 1, "ADAPTIVE_TRAINING_OR_SELECTION"),
    ("practice_cycles_per_weather", 2, "CYCLE_BUDGET"),
    ("understanding_in_core", True, "CORE_OR_EVIDENCE_BOUNDARY"),
    ("emotion_reporting_requires_understanding_pass", True, "CORE_OR_EVIDENCE_BOUNDARY"),
    ("formal_runtime_mock_allowed", True, "CORE_OR_EVIDENCE_BOUNDARY"),
    ("core_demo_extra_budget", True, "CORE_OR_EVIDENCE_BOUNDARY"),
    ("layers", ["target"], "LAYER_COVERAGE"),
])
def test_contract_mutations(key, value, code):
    c, b, r = inputs()
    c[key] = copy.deepcopy(value)
    assert code in V["validate"](c, b, r)


def test_old_timing_rejected():
    c, b, r = inputs()
    c["timeline"][1], c["timeline"][3] = c["timeline"][3], c["timeline"][1]
    assert "TIMELINE_ORDER" in V["validate"](c, b, r)


def test_slow_cycles_do_not_fit():
    c, b, r = inputs()
    b["modules"]["storm"]["steps"][0]["duration_seconds"] = 10
    assert "CYCLES_DO_NOT_FIT:storm" in V["validate"](c, b, r)


@pytest.mark.parametrize("key,value", [
    ("record_kind", "OBSERVED"), ("actual_training_seconds", 180),
    ("mastery_time_seconds", 180), ("training_contract_id", "wrong"),
])
def test_template_does_not_claim_data(key, value):
    c, b, r = inputs()
    r[key] = value
    assert "TEMPLATE_PRESENTS_OBSERVATION" in V["validate"](c, b, r)
