"""Check current governance adoption without granting runtime or research authority."""
import csv
import hashlib
import json
import runpy
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV = HERE.parent
PLAN = GOV.parent
REPO = GOV.parents[3]
ADAPTER = PLAN.parent / "2026-09-08_SRP_v1.2_当前基线适配包"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def semantic_errors(rows, protocol, milestones):
    by_id = {r["task_id"]: r for r in rows}
    errors = []
    if len(rows) != 71 or len(by_id) != 71:
        errors.append("TASK_IDENTITY_COUNT")
    if protocol["formal_participant_collection_allowed"] is not False:
        errors.append("FORMAL_COLLECTION_NOT_BLOCKED")
    if protocol["primary"]["contrast"] != "native_minus_abstract":
        errors.append("PRIMARY_DIRECTION")
    if not protocol["primary"]["report_even_if_functional_guard_fails"]:
        errors.append("AFFECT_REPORTING_GATED")
    if protocol["equivalence"]["confirmatory_enabled"] or protocol["sample_planning"]["formal_randomized_n"] is not None:
        errors.append("UNAPPROVED_NUMERIC_FREEZE")
    if "A-03-CAL" not in by_id["U12-11"]["depends_on"].split("|"):
        errors.append("CALIBRATION_MUST_PRECEDE_FREEZE")
    real = next(m for m in milestones["milestones"] if m["id"] == "A-03-REAL")
    if "U12-04" not in real["depends_on"]:
        errors.append("NEW_SPEC_REQUIRED")
    if "U12-12" not in by_id["W-04"]["depends_on"].split("|"):
        errors.append("HANDOFF_HAS_NO_CONSUMER")
    return errors


def main():
    with (GOV / "05_可领取任务包.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    profile = runpy.run_path(str(GOV / "governance_profile.py"))["load_profile"](GOV)
    errors = semantic_errors(rows, read(PLAN / "00_总控/protocol_authority_v1.2.json"), read(profile["milestones"]))
    with (ADAPTER / "baseline/05_可领取任务包.csv").open(encoding="utf-8-sig", newline="") as f:
        baseline = list(csv.DictReader(f))
    by_id = {r["task_id"]: r for r in rows}
    governance = runpy.run_path(str(GOV / "governance_profile.py"))
    states = {key: row["status"] for key, row in by_id.items()}
    states.update(read(GOV / "audit_upgrade/task_milestone_status_v1.0.json")["statuses"])
    for row in rows:
        incomplete = {d for d in row["depends_on"].split("|") if d and states.get(d) != "DONE"}
        errors.extend(governance["validate_u12_acceptance"](row, incomplete, GOV))
    for row in baseline:
        if row["status"] == "DONE" or row["task_id"] == "A-03":
            if row != by_id[row["task_id"]]:
                errors.append("SIGNED_OR_CLAIMED_SCOPE_DRIFT:" + row["task_id"])
    for name in ("release_routes_v1.0.json", "task_milestones_v1.0.json", "task_milestone_status_v1.0.json", "upgrade_subdeliveries_v1.0.csv"):
        live = (GOV / "audit_upgrade" / name).read_bytes().replace(b"\r\n", b"\n")
        previous = (ADAPTER / "baseline" / name).read_bytes().replace(b"\r\n", b"\n")
        if live != previous:
            errors.append("LEGACY_CONTRACT_CHANGED:" + name)
    for entry in read(HERE / "consumers.json")["entries"]:
        root = PLAN if entry["root"] == "plan" else REPO
        if not (root / entry["path"]).is_file() or entry["owner"] not in by_id:
            errors.append("CONSUMER_UNRESOLVED:" + entry["id"])
    relative = (GOV / "当前解锁独立任务包/A-03/package_manifest.json").relative_to(REPO).as_posix()
    old = json.loads(subprocess.check_output(["git", "show", "bdda9f9:" + relative], cwd=REPO))
    if read(REPO / relative)["input_snapshot_id"] != old["input_snapshot_id"]:
        errors.append("A03_FROZEN_INPUT_CHANGED")
    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1
    print("PASS: governance v1.2; 71 tasks; signed history preserved; formal collection blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
