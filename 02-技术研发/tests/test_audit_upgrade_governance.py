from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPGRADE = (
    PROJECT_ROOT
    / "00-项目管理/01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
    / "24_团队任务与项目治理/audit_upgrade"
)


def load_route_module():
    path = UPGRADE / "route_evaluator.py"
    spec = importlib.util.spec_from_file_location("srp_route_evaluator", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_governance_script(name: str):
    path = UPGRADE.parent / name
    spec = importlib.util.spec_from_file_location(f"srp_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def receipt(scope: str) -> dict[str, str]:
    return {
        "record_id": "fixture-route-1",
        "candidate_identity": "fixture-candidate",
        "reviewer": "fixture-reviewer",
        "review_method": "record_review",
        "signed_ref": "fixture-only",
        "signed_ref_sha256": "0" * 64,
        "status": "PASS",
        "scope": scope,
    }


def stage3_activity(tmp_path: Path, active_source: str | None = None) -> dict[str, dict]:
    result = {}
    for source in (
        "stage3_assignment_ledger",
        "stage3_exposure_ledger",
        "B-03_instance_registry",
    ):
        path = tmp_path / f"{source}.jsonl"
        content = (json.dumps({"event": "stage3"}) + "\n").encode() if source == active_source else b""
        path.write_bytes(content)
        result[source] = {
            "path": path.name,
            "byte_sha256": hashlib.sha256(content).hexdigest().upper(),
            "record_count": 1 if content else 0,
        }
    return result


def test_stage1_route_closes_without_stage3_tasks(tmp_path: Path):
    module = load_route_module()
    result = module.evaluate_route(
        "stage1_only", {"A-05", "W-01"}, stage3_activity(tmp_path), receipt("NO_STAGE3"), evidence_root=tmp_path
    )
    assert result["ok"]
    assert result["authorization"] is False


def test_stage1_route_cannot_hide_stage3_activity(tmp_path: Path):
    module = load_route_module()
    activity = stage3_activity(tmp_path, "stage3_exposure_ledger")
    result = module.evaluate_route(
        "stage1_only", {"A-05", "W-01"}, activity, receipt("NO_STAGE3"), evidence_root=tmp_path
    )
    assert "CANNOT_HIDE_STAGE3_ACTIVITY" in result["errors"]


def test_stage3_route_requires_a04_and_all_result_families(tmp_path: Path):
    module = load_route_module()
    activity = stage3_activity(tmp_path, "B-03_instance_registry")
    result = module.evaluate_route(
        "with_stage3",
        {"A-05", "W-01"},
        activity,
        receipt("INCLUDE_STAGE3"),
        {"stage3_results"},
        evidence_root=tmp_path,
    )
    assert "MISSING_TASKS:A-04" in result["errors"]
    assert any(item.startswith("MISSING_RESULT_FAMILIES:") for item in result["errors"])


def test_invalid_activity_count_fails_closed(tmp_path: Path):
    module = load_route_module()
    activity = stage3_activity(tmp_path)
    activity["stage3_assignment_ledger"]["record_count"] = -1
    result = module.evaluate_route(
        "stage1_only", {"A-05", "W-01"}, activity, receipt("NO_STAGE3"), evidence_root=tmp_path
    )
    assert "INVALID_STAGE3_ACTIVITY_EVIDENCE" in result["errors"]


def test_stage3_activity_sources_cannot_share_one_ledger(tmp_path: Path):
    module = load_route_module()
    activity = stage3_activity(tmp_path)
    activity["stage3_exposure_ledger"] = dict(activity["stage3_assignment_ledger"])
    result = module.evaluate_route(
        "stage1_only", {"A-05", "W-01"}, activity, receipt("NO_STAGE3"), evidence_root=tmp_path
    )
    assert "INVALID_STAGE3_ACTIVITY_EVIDENCE" in result["errors"]


def test_unknown_dependency_and_placeholder_reviewer_are_rejected():
    validator = load_governance_script("07_validate_task_packages.py")
    assert validator.unknown_dependencies({"KNOWN", "MISSING"}, {"KNOWN"}) == {"MISSING"}
    assert validator.reviewer_is_placeholder("待复核")
    assert not validator.reviewer_is_placeholder("傅钧烨（团队总监，独立第二人复核）")


def test_conditional_edges_participate_in_cycle_detection():
    validator = load_governance_script("07_validate_task_packages.py")
    graph = {"A": {"B"}, "B": set()}
    graph["B"].add("A")
    assert validator.dependency_cycle_nodes(graph)


def test_a06_fake_candidate_and_missing_signed_report_are_rejected():
    validator = load_governance_script("15_validate_audit_upgrade.py")
    errors = validator.validate_a06_receipt(
        {
            "candidate_identity": "fake", "reviewer": "someone",
            "signed_ref": "missing.md", "signed_ref_sha256": "0" * 64,
            "record_id": "route-1", "scope": "NO_STAGE3",
        }
    )
    assert "A06_RECEIPT_CANDIDATE_NOT_A_COMMIT" in errors
    assert "A06_SIGNED_REPORT_MISSING" in errors


def test_external_capability_record_identity_is_recomputed(tmp_path: Path):
    validator = load_governance_script("15_validate_audit_upgrade.py")
    validator.PROJECT_ROOT = tmp_path.resolve()
    validator.git_tracks = lambda _relative: True
    receipt = tmp_path / "receipt.md"
    receipt.write_text("signed", encoding="utf-8")
    digest = hashlib.sha256(receipt.read_bytes()).hexdigest().upper()
    identity = hashlib.sha256(f"receipt.md:{digest}".encode("utf-8")).hexdigest().upper()
    record = {
        "record_id": "cap-1",
        "record_type": "external_capability",
        "scope": "INSTITUTION_LEVEL_A",
        "candidate_identity": identity,
        "source_commit": None,
        "input_snapshot_id": None,
        "evidence_refs": ["receipt.md"],
        "review": {
            "status": "PASS",
            "reviewer": "external-owner",
            "role": "authority",
            "method": "external_receipt",
            "signed_ref": "receipt.md",
        },
    }
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert validator.validate_external_capability_record(
        "INSTITUTION_LEVEL_A", "record.json"
    ) == []
    record["candidate_identity"] = "0" * 64
    path.write_text(json.dumps(record), encoding="utf-8")
    assert any(
        "EVIDENCE_IDENTITY_MISMATCH" in item
        for item in validator.validate_external_capability_record(
            "INSTITUTION_LEVEL_A", "record.json"
        )
    )


def test_in_progress_and_review_snapshots_fail_closed_on_drift():
    renderer = load_governance_script("13_render_ready_task_packages.py")
    for status in ("IN_PROGRESS", "IN_REVIEW"):
        try:
            renderer.enforce_snapshot_freeze(status, "OLD", "NEW")
        except ValueError as exc:
            assert "input snapshot changed" in str(exc)
        else:
            raise AssertionError(f"{status} drift was accepted")
    renderer.enforce_snapshot_freeze("READY", "OLD", "NEW")
    for status in ("IN_PROGRESS", "IN_REVIEW"):
        try:
            renderer.enforce_snapshot_freeze(status, None, "NEW")
        except ValueError:
            pass
        else:
            raise AssertionError(f"{status} accepted a missing input baseline")


def test_input_drift_writes_deterministic_impact_record(tmp_path: Path):
    renderer = load_governance_script("13_render_ready_task_packages.py")
    path = renderer.write_input_impact(
        tmp_path, "U-01", "IN_PROGRESS", "A" * 64, "B" * 64
    )
    first = path.read_bytes()
    repeated = renderer.write_input_impact(
        tmp_path, "U-01", "IN_PROGRESS", "A" * 64, "B" * 64
    )
    assert repeated == path
    assert repeated.read_bytes() == first
    assert "REFRESH_BLOCKED_PENDING_TASK_OWNER_REVIEW" in first.decode("utf-8")
    missing = renderer.write_input_impact(
        tmp_path, "U-02", "IN_REVIEW", None, "C" * 64
    )
    assert "MISSING" in missing.name


def test_package_refresh_preserves_member_files(tmp_path: Path):
    renderer = load_governance_script("13_render_ready_task_packages.py")
    output = tmp_path / "output"
    build = tmp_path / "build"
    old_task = output / "T-02"
    new_task = build / "T-02"
    (old_task / "member").mkdir(parents=True)
    (new_task / "inputs").mkdir(parents=True)
    (old_task / "member" / "result.md").write_text("owned", encoding="utf-8")
    (old_task / "TASK.md").write_text("old generated", encoding="utf-8")
    (new_task / "TASK.md").write_text("new generated", encoding="utf-8")

    renderer.preserve_task_owned_files(output, build, {"T-02"}, tmp_path / "retired")

    assert (new_task / "member" / "result.md").read_text(encoding="utf-8") == "owned"
    assert (new_task / "TASK.md").read_text(encoding="utf-8") == "new generated"


def test_package_refresh_archives_files_for_task_leaving_dispatch(tmp_path: Path):
    renderer = load_governance_script("13_render_ready_task_packages.py")
    output = tmp_path / "output"
    build = tmp_path / "build"
    retired = tmp_path / "retired"
    old_task = output / "U-01"
    (old_task / "member").mkdir(parents=True)
    build.mkdir()
    (old_task / "member" / "handoff.md").write_text("keep", encoding="utf-8")

    renderer.preserve_task_owned_files(output, build, set(), retired)

    assert (retired / "U-01" / "member" / "handoff.md").read_text(encoding="utf-8") == "keep"
