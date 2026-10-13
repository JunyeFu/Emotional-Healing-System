from __future__ import annotations

import copy
import csv
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
GOV = PLAN / "24_团队任务与项目治理"


def context():
    with (GOV / "05_可领取任务包.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    protocol = json.loads((PLAN / "00_总控/protocol_authority_v1.2.json").read_text(encoding="utf-8"))
    milestones = json.loads((GOV / "audit_upgrade/task_milestones_v1.2.json").read_text(encoding="utf-8"))
    return rows, protocol, milestones


def errors(rows, protocol, milestones):
    return runpy.run_path(str(GOV / "u12_upgrade/validate_u12_governance.py"))["semantic_errors"](rows, protocol, milestones)


def test_current_governance_semantics():
    assert errors(*context()) == []


def test_versions_resolve_distinct_contracts(tmp_path):
    load = runpy.run_path(str(GOV / "governance_profile.py"))["load_profile"]
    assert load(tmp_path)["count"] == 59
    (tmp_path / "active_governance.json").write_text('{"version":"1.2"}', encoding="utf-8")
    assert load(tmp_path)["count"] == 71
    assert load(tmp_path)["routes"].name == "release_routes_v1.2.json"


def test_unknown_version_rejected(tmp_path):
    load = runpy.run_path(str(GOV / "governance_profile.py"))["load_profile"]
    (tmp_path / "active_governance.json").write_text('{"version":"9.9"}', encoding="utf-8")
    with pytest.raises(ValueError, match="UNKNOWN_GOVERNANCE_VERSION"):
        load(tmp_path)


@pytest.mark.parametrize("mutation,expected", [
    ("formal", "FORMAL_COLLECTION_NOT_BLOCKED"),
    ("direction", "PRIMARY_DIRECTION"),
    ("gated", "AFFECT_REPORTING_GATED"),
    ("equivalence", "UNAPPROVED_NUMERIC_FREEZE"),
    ("sample", "UNAPPROVED_NUMERIC_FREEZE"),
    ("calibration", "CALIBRATION_MUST_PRECEDE_FREEZE"),
    ("spec", "NEW_SPEC_REQUIRED"),
    ("handoff", "HANDOFF_HAS_NO_CONSUMER"),
])
def test_unapproved_semantic_changes_rejected(mutation, expected):
    rows, p, m = context()
    by_id = {r["task_id"]: r for r in rows}
    if mutation == "formal": p["formal_participant_collection_allowed"] = True
    if mutation == "direction": p["primary"]["contrast"] = "abstract_minus_native"
    if mutation == "gated": p["primary"]["report_even_if_functional_guard_fails"] = False
    if mutation == "equivalence": p["equivalence"]["confirmatory_enabled"] = True
    if mutation == "sample": p["sample_planning"]["formal_randomized_n"] = 192
    if mutation == "calibration": by_id["U12-11"]["depends_on"] = "G-05|E-03|U12-09"
    if mutation == "spec": m["milestones"][1]["depends_on"].remove("U12-04")
    if mutation == "handoff": by_id["W-04"]["depends_on"] = "W-03"
    assert expected in errors(rows, p, m)


def test_current_route_uses_u12_result_review(tmp_path):
    namespace = runpy.run_path(str(GOV / "audit_upgrade/route_evaluator.py"))
    assert namespace["CONTRACT"].name == "release_routes_v1.2.json"
    contract = json.loads(namespace["CONTRACT"].read_text(encoding="utf-8"))
    assert "U12-10" in contract["routes"]["stage1_only"]["required_done"]
    assert "U12-08" in contract["routes"]["with_stage3"]["required_done"]
    assert "A-04" not in contract["routes"]["stage1_only"]["required_done"]


def test_new_task_closure_has_all_consumers():
    validator = runpy.run_path(str(GOV / "07_validate_task_packages.py"))
    rows, _, milestones = context()
    graph = {r["task_id"]: set(filter(None, r["depends_on"].split("|"))) for r in rows}
    route = json.loads((GOV / "audit_upgrade/release_routes_v1.2.json").read_text(encoding="utf-8"))
    for edge in route["conditional_edges"]:
        graph[edge["to"]].add(edge["from"])
    full = validator["combined_dependency_graph"](graph, milestones["milestones"], "A-03")
    assert len(full) == 74
    assert not validator["dependency_cycle_nodes"](full)


def test_historical_acceptance_and_frozen_input_preserved():
    validator = runpy.run_path(str(GOV / "u12_upgrade/validate_u12_governance.py"))
    assert validator["main"]() == 0


def test_done_requires_dependencies_and_human_evidence(tmp_path):
    validate = runpy.run_path(str(GOV / "governance_profile.py"))["validate_u12_acceptance"]
    issues = validate({"task_id": "U12-02", "status": "DONE"}, ["U12-01"], tmp_path)
    assert "U12-02:DONE_WITH_INCOMPLETE_DEPENDENCIES" in issues
    assert "U12-02:HUMAN_ACCEPTANCE_MISSING" in issues


@pytest.mark.parametrize("task_id,status", [("F-01", "DONE"), ("A-03", "IN_PROGRESS")])
def test_candidate_cannot_rewrite_protected_rows(task_id, status):
    validate = runpy.run_path(str(GOV / "u12_upgrade/apply_governance.py"))["validate_preserved_rows"]
    baseline = [{"task_id": task_id, "status": status, "reviewer": "original"}]
    validate(copy.deepcopy(baseline), baseline)
    candidate = copy.deepcopy(baseline)
    candidate[0]["reviewer"] = "changed"
    with pytest.raises(ValueError, match="PROTECTED_CANDIDATE_ROW_DRIFT"):
        validate(candidate, baseline)


def test_legacy_binding_tamper_rejected(tmp_path, monkeypatch):
    module = runpy.run_path(str(GOV / "u12_upgrade/freeze_legacy_evidence.py"))
    validate = module["validate"]
    path = tmp_path / "binding.json"
    value = module["expected_binding"]()
    value["commit"] = "0" * 40
    path.write_text(json.dumps(value), encoding="utf-8")
    monkeypatch.setitem(validate.__globals__, "OUTPUT", path)
    assert validate() == ["LEGACY_GIT_BINDING_MISMATCH"]


def test_duplicate_candidate_cannot_hide_protected_row():
    validate = runpy.run_path(str(GOV / "u12_upgrade/apply_governance.py"))["validate_preserved_rows"]
    baseline = [{"task_id": "F-01", "status": "DONE"}]
    with pytest.raises(ValueError, match="DUPLICATE_CANDIDATE_TASK_ID"):
        validate([{"task_id": "F-01", "status": "READY"}, *baseline], baseline)


@pytest.mark.parametrize("claimant,independent,human", [
    ("Alice", "Alice", "Alice"), ("Alice", "Bob", "Alice"),
    ("Alice", "Bob", "Bob"), (" Alice ", "alice", "Bob"),
])
def test_self_review_rejected(tmp_path, claimant, independent, human):
    validate = runpy.run_path(str(GOV / "governance_profile.py"))["validate_u12_acceptance"]
    root = tmp_path / "repo/a/b/c/governance"
    acceptance = root / "u12_upgrade/acceptance"
    acceptance.mkdir(parents=True)
    (acceptance / "U12-01.json").write_text(json.dumps({
        "task_id": "U12-01", "candidate_commit": "invalid",
        "independent_review": {"reviewer": independent},
        "human_review": {"reviewer": human},
    }), encoding="utf-8")
    issues = validate({"task_id": "U12-01", "status": "DONE", "claimant": claimant}, [], root)
    assert "U12-01:REVIEWER_SEPARATION_REQUIRED" in issues
