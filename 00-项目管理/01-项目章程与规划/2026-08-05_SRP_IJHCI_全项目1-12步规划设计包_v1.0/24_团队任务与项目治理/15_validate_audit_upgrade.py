"""Validate the audit-upgrade governance contracts without external side effects."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[3]
UPGRADE = ROOT / "audit_upgrade"
REGISTRY = ROOT / "05_可领取任务包.csv"


def project_file(relative: str) -> Path | None:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        return None
    path = (PROJECT_ROOT / relative).resolve()
    if PROJECT_ROOT not in path.parents or not path.is_file():
        return None
    return path


def git_commit_exists(candidate: str) -> bool:
    if re.fullmatch(r"[0-9a-fA-F]{40}", candidate or "") is None:
        return False
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{candidate}^{{commit}}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def git_tracks(relative: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def validate_external_capability_record(capability_id: str, relative: str) -> list[str]:
    path = project_file(relative)
    if path is None:
        return [f"{capability_id}:EVIDENCE_RECORD_MISSING"]
    if not git_tracks(relative):
        return [f"{capability_id}:EVIDENCE_RECORD_NOT_TRACKED"]
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [f"{capability_id}:EVIDENCE_RECORD_INVALID_JSON"]
    review = record.get("review", {})
    refs = record.get("evidence_refs", [])
    errors: list[str] = []
    expected_fields = {
        "record_id", "record_type", "scope", "candidate_identity", "source_commit",
        "input_snapshot_id", "evidence_refs", "review",
    }
    expected_review_fields = {"status", "reviewer", "role", "method", "signed_ref"}
    if set(record) != expected_fields or not isinstance(review, dict) or set(review) != expected_review_fields:
        errors.append(f"{capability_id}:EVIDENCE_RECORD_SCHEMA_MISMATCH")
    if not isinstance(record.get("record_id"), str) or not record["record_id"].strip():
        errors.append(f"{capability_id}:EVIDENCE_RECORD_ID_INVALID")
    if record.get("record_type") != "external_capability" or record.get("scope") != capability_id:
        errors.append(f"{capability_id}:EVIDENCE_SCOPE_MISMATCH")
    if review.get("status") != "PASS" or review.get("method") != "external_receipt":
        errors.append(f"{capability_id}:EXTERNAL_REVIEW_NOT_PASS")
    reviewer = str(review.get("reviewer", "")).strip()
    if not reviewer or reviewer.casefold() in {"待填写", "tbd", "pending"}:
        errors.append(f"{capability_id}:EXTERNAL_REVIEWER_INVALID")
    if not isinstance(refs, list) or not refs:
        errors.append(f"{capability_id}:EVIDENCE_REFS_MISSING")
        return errors
    resolved = [(ref, project_file(ref)) for ref in refs]
    if any(path is None for _, path in resolved):
        errors.append(f"{capability_id}:EVIDENCE_REF_UNAVAILABLE")
        return errors
    if any(not git_tracks(ref) for ref, _ in resolved):
        errors.append(f"{capability_id}:EVIDENCE_REF_NOT_TRACKED")
        return errors
    identity_payload = "\n".join(
        f"{ref}:{hashlib.sha256(ref_path.read_bytes()).hexdigest().upper()}"
        for ref, ref_path in sorted(resolved)
    ).encode("utf-8")
    expected_identity = hashlib.sha256(identity_payload).hexdigest().upper()
    if record.get("candidate_identity") != expected_identity:
        errors.append(f"{capability_id}:EVIDENCE_IDENTITY_MISMATCH")
    signed_ref = review.get("signed_ref")
    if signed_ref not in refs:
        errors.append(f"{capability_id}:SIGNED_REF_NOT_IN_EVIDENCE")
    return errors


def validate_a06_receipt(receipt: dict[str, object]) -> list[str]:
    errors: list[str] = []
    candidate = str(receipt.get("candidate_identity", ""))
    reviewer = str(receipt.get("reviewer", ""))
    signed_ref = str(receipt.get("signed_ref", ""))
    record_id = str(receipt.get("record_id", ""))
    scope = str(receipt.get("scope", ""))
    if not git_commit_exists(candidate):
        errors.append("A06_RECEIPT_CANDIDATE_NOT_A_COMMIT")
    report = project_file(signed_ref)
    if report is None:
        errors.append("A06_SIGNED_REPORT_MISSING")
    else:
        if not git_tracks(signed_ref):
            errors.append("A06_SIGNED_REPORT_NOT_TRACKED")
        try:
            text = report.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            errors.append("A06_SIGNED_REPORT_NOT_TEXT")
        else:
            report_hash = hashlib.sha256(report.read_bytes()).hexdigest().upper()
            if report_hash != receipt.get("signed_ref_sha256"):
                errors.append("A06_SIGNED_REPORT_HASH_MISMATCH")
            if any(marker not in text for marker in (candidate, reviewer, record_id, scope, "PASS")):
                errors.append("A06_SIGNED_REPORT_IDENTITY_MISMATCH")
    return errors


def main() -> int:
    errors: list[str] = []
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["task_id"]: row for row in rows}
    templates = {row["task_id"] for row in rows if row["kind"] == "TEMPLATE"}
    if len(rows) != 59 or len(by_id) != 59:
        errors.append("REGISTRY_MUST_HAVE_59_UNIQUE_TASKS")
    if len(rows) - len(templates) != 56 or templates != {"B-01", "B-02", "B-03"}:
        errors.append("REGISTRY_KIND_COUNTS_INVALID")
    if by_id.get("A-06", {}).get("depends_on") != "A-05":
        errors.append("A06_UNCONDITIONAL_DEPENDENCY_INVALID")
    if by_id.get("W-02", {}).get("depends_on") != "W-01|A-06":
        errors.append("W02_ROUTE_DEPENDENCY_INVALID")

    source = json.loads((UPGRADE / "source_record_v1.0.json").read_text(encoding="utf-8"))
    archived = ROOT / source.get("archived_path", "")
    if not archived.is_file():
        errors.append("AUDIT_SOURCE_ARCHIVE_MISSING")
    else:
        content = archived.read_bytes()
        if len(content) != source.get("source_bytes"):
            errors.append("AUDIT_SOURCE_SIZE_MISMATCH")
        if hashlib.sha256(content).hexdigest().upper() != source.get("source_byte_sha256"):
            errors.append("AUDIT_SOURCE_HASH_MISMATCH")

    routes = json.loads((UPGRADE / "release_routes_v1.0.json").read_text(encoding="utf-8"))
    if set(routes.get("routes", {})) != {"stage1_only", "with_stage3"}:
        errors.append("RELEASE_ROUTES_INVALID")
    if routes.get("stage3_started_evidence_sources") != [
        "stage3_assignment_ledger", "stage3_exposure_ledger", "B-03_instance_registry"
    ]:
        errors.append("STAGE3_ACTIVITY_SOURCES_INVALID")

    milestones = json.loads((UPGRADE / "task_milestones_v1.0.json").read_text(encoding="utf-8"))
    milestone_ids = {item["id"] for item in milestones.get("milestones", [])}
    if milestone_ids != {"A-03-SPEC", "A-03-REAL", "A-03-CAL"}:
        errors.append("A03_MILESTONES_INVALID")

    with (UPGRADE / "external_capability_matrix_v1.0.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        capabilities = list(csv.DictReader(handle))
    required_capabilities = {
        "INSTITUTION_LEVEL_A", "INSTITUTION_LEVEL_B", "INSTITUTION_LEVEL_C",
        "INSTITUTION_STAGE1", "INSTITUTION_STAGE3", "QUESTIONNAIRE_PERMISSION",
        "RETENTION_AND_PRIVACY", "FORMAL_MACHINE", "ASSET_EXPERIMENT_USE",
        "ASSET_PUBLICATION_USE", "ASSET_REDISTRIBUTION",
        "STATION_CAPACITY_STAGE1", "STATION_CAPACITY_STAGE3",
    }
    if {row["capability_id"] for row in capabilities} != required_capabilities:
        errors.append("CAPABILITY_MATRIX_INVALID")
    if any(row["status"] not in {"PENDING_EXTERNAL", "QUALIFIED"} for row in capabilities):
        errors.append("EXTERNAL_CAPABILITY_STATUS_INVALID")
    if any(
        (row["status"] == "QUALIFIED" and not row["evidence_ref"].strip())
        or (row["status"] == "PENDING_EXTERNAL" and row["evidence_ref"].strip())
        for row in capabilities
    ):
        errors.append("EXTERNAL_CAPABILITY_EVIDENCE_STATE_MISMATCH")
    if by_id.get("G-05", {}).get("status") == "DONE" and any(
        row["status"] != "QUALIFIED" or not row["evidence_ref"].strip()
        for row in capabilities
    ):
        errors.append("G05_DONE_WITHOUT_ALL_ACTIVITY_QUALIFICATIONS")
    for capability in capabilities:
        if capability["status"] == "QUALIFIED":
            errors.extend(
                validate_external_capability_record(
                    capability["capability_id"], capability["evidence_ref"]
                )
            )

    with (UPGRADE / "findings_disposition_v1.0.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        findings = list(csv.DictReader(handle))
    if len(findings) != 24 or len({row["finding_id"] for row in findings}) != 24:
        errors.append("FINDINGS_DISPOSITION_INVALID")
    n05 = next((row for row in findings if row["finding_id"] == "N05"), None)
    if not n05 or n05["local_disposition"] != "NOT_ADOPTED_POLICY_CONFLICT":
        errors.append("N05_POLICY_DECISION_MISSING")

    with (UPGRADE / "upgrade_subdeliveries_v1.0.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        subdeliveries = list(csv.DictReader(handle))
    expected_subdeliveries = {f"UP-{index:02d}" for index in range(1, 13)}
    if {row["subdelivery_id"] for row in subdeliveries} != expected_subdeliveries:
        errors.append("UPGRADE_SUBDELIVERIES_INVALID")
    if any(not row["owner_tasks"] or not row["status"] or not row["completion_gate"] for row in subdeliveries):
        errors.append("UPGRADE_SUBDELIVERY_FIELDS_MISSING")
    valid_upgrade_statuses = {
        "IMPLEMENTED_CANDIDATE", "FOUNDATION_IMPLEMENTED", "PLANNED_WAIT_DEP",
        "WAIT_DEP", "WAIT_DEP_EXTERNAL",
    }
    upgrade_graph: dict[str, set[str]] = {}
    for row in subdeliveries:
        upgrade_id = row["subdelivery_id"]
        owners = {item for item in row["owner_tasks"].split("|") if item}
        dependencies = {item for item in row["depends_on"].split("|") if item}
        upgrade_graph[upgrade_id] = dependencies
        if owners - set(by_id):
            errors.append(f"{upgrade_id}:UNKNOWN_OWNER_TASKS")
        if dependencies - expected_subdeliveries:
            errors.append(f"{upgrade_id}:UNKNOWN_UPGRADE_DEPENDENCIES")
        if row["status"] not in valid_upgrade_statuses:
            errors.append(f"{upgrade_id}:INVALID_UPGRADE_STATUS")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit_upgrade(upgrade_id: str) -> None:
        if upgrade_id in visiting:
            errors.append(f"{upgrade_id}:UPGRADE_DEPENDENCY_CYCLE")
            return
        if upgrade_id in visited:
            return
        visiting.add(upgrade_id)
        for dependency in upgrade_graph.get(upgrade_id, set()):
            visit_upgrade(dependency)
        visiting.remove(upgrade_id)
        visited.add(upgrade_id)

    for upgrade_id in upgrade_graph:
        visit_upgrade(upgrade_id)

    evidence_manifest_path = UPGRADE / "upgrade_evidence_manifest_v1.0.json"
    if not evidence_manifest_path.is_file():
        errors.append("UPGRADE_EVIDENCE_MANIFEST_MISSING")
    else:
        evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
        manifest_entries = evidence_manifest.get("entries", {})
        if evidence_manifest.get("schema_version") != "1.0" or set(manifest_entries) != expected_subdeliveries:
            errors.append("UPGRADE_EVIDENCE_MANIFEST_INVALID")
        resolver_path = UPGRADE / "build_upgrade_evidence_manifest.py"
        spec = importlib.util.spec_from_file_location("srp_upgrade_evidence", resolver_path)
        resolver = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            errors.append("UPGRADE_EVIDENCE_RESOLVER_UNAVAILABLE")
        else:
            spec.loader.exec_module(resolver)
            for row in subdeliveries:
                upgrade_id = row["subdelivery_id"]
                expected_refs = [item for item in row["evidence_refs"].split("|") if item]
                recorded = manifest_entries.get(upgrade_id, [])
                if [item.get("reference") for item in recorded] != expected_refs:
                    errors.append(f"{upgrade_id}:EVIDENCE_REFERENCE_LIST_MISMATCH")
                    continue
                for item in recorded:
                    try:
                        evidence_path = resolver.resolve_ref(item["reference"])
                    except (KeyError, ValueError):
                        errors.append(f"{upgrade_id}:EVIDENCE_REFERENCE_UNAVAILABLE")
                        continue
                    observed = hashlib.sha256(evidence_path.read_bytes()).hexdigest().upper()
                    if observed != item.get("byte_sha256"):
                        errors.append(f"{upgrade_id}:EVIDENCE_HASH_MISMATCH")

    if by_id.get("A-06", {}).get("status") == "DONE":
        closure_path = UPGRADE / "a06_route_closure_v1.json"
        if not closure_path.is_file():
            errors.append("A06_DONE_WITHOUT_ROUTE_CLOSURE")
        else:
            closure = json.loads(closure_path.read_text(encoding="utf-8"))
            expected_closure_fields = {
                "schema_version", "route", "activity_evidence", "receipt", "result_families"
            }
            if closure.get("schema_version") != "1.0" or set(closure) != expected_closure_fields:
                errors.append("A06_ROUTE_CLOSURE_SCHEMA_MISMATCH")
            module_path = UPGRADE / "route_evaluator.py"
            spec = importlib.util.spec_from_file_location("srp_route_evaluator", module_path)
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                errors.append("A06_ROUTE_EVALUATOR_UNAVAILABLE")
            else:
                spec.loader.exec_module(module)
                result = module.evaluate_route(
                    closure.get("route", ""),
                    {task_id for task_id, row in by_id.items() if row["status"] == "DONE"},
                    closure.get("activity_evidence", {}),
                    closure.get("receipt", {}),
                    set(closure.get("result_families", [])),
                    evidence_root=Path(os.environ.get("SRP_A06_EVIDENCE_ROOT", "")),
                )
                if not result["ok"]:
                    errors.append("A06_ROUTE_CLOSURE_INVALID:" + ",".join(result["errors"]))
                errors.extend(validate_a06_receipt(closure.get("receipt", {})))

    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("PASS: audit upgrade batch0-1 contracts; tasks=59; fixed=56; findings=24; upgrades=12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
