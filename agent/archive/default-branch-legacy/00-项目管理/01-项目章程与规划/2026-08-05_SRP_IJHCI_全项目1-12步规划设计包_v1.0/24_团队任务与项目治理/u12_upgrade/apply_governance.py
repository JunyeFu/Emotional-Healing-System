"""Apply the reviewed, local governance adaptation; no runtime or external actions."""
import argparse
import copy
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV = HERE.parent
PLAN = GOV.parent
REPO = GOV.parents[3]
ADAPTER = PLAN.parent / "2026-09-08_SRP_v1.2_当前基线适配包"
REGISTRY = GOV / "05_可领取任务包.csv"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def validate_preserved_rows(candidate, baseline):
    by_id = {r["task_id"]: r for r in candidate}
    if len(by_id) != len(candidate):
        raise ValueError("DUPLICATE_CANDIDATE_TASK_ID")
    for row in baseline:
        if row["status"] == "DONE" or row["task_id"] == "A-03":
            if by_id.get(row["task_id"]) != row:
                raise ValueError("PROTECTED_CANDIDATE_ROW_DRIFT:" + row["task_id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--state", choices=["READY", "IN_PROGRESS", "IN_REVIEW"])
    parser.add_argument("--candidate")
    args = parser.parse_args()
    if args.state:
        with REGISTRY.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        row = next(r for r in rows if r["task_id"] == "U12-01")
        if row["status"] == "DONE":
            raise ValueError("SIGNED_TASK_IMMUTABLE")
        if args.state == "READY" and (GOV / "当前解锁独立任务包/U12-01").exists():
            raise ValueError("INPUT_ALREADY_FROZEN")
        if args.state == "IN_REVIEW" and not args.candidate:
            raise ValueError("REVIEW_REQUIRES_COMMIT")
        if args.state == "IN_REVIEW" and row["status"] not in {"IN_PROGRESS", "IN_REVIEW"}:
            raise ValueError("INVALID_REVIEW_TRANSITION")
        if args.candidate and (not re.fullmatch(r"[0-9a-f]{40}", args.candidate) or subprocess.run(
            ["git", "cat-file", "-e", args.candidate + "^{commit}"], cwd=REPO, capture_output=True
        ).returncode):
            raise ValueError("INVALID_CANDIDATE_COMMIT")
        row.update(status=args.state, claimant="" if args.state == "READY" else "Codex",
                   branch="" if args.state == "READY" else "codex/u12-01-governance-migration",
                   reviewer="独立Agent复核；真实第二人签收另记" if args.state == "IN_REVIEW" else "")
        if args.candidate:
            mapping_path = GOV / "12_独立任务包文件映射_v1.0.json"
            mapping = read(mapping_path)
            mapping["tasks"]["U12-01"]["implementation_commit"] = args.candidate
            write(mapping_path, mapping)
        with REGISTRY.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print("U12-01 state:", args.state)
        return
    identity = read(ADAPTER / "source_manifest.json")
    # The receiving worktree may contain user assets. Only authority inputs are checked.
    for entry in identity["baseline_files"]:
        live = (REPO / entry["repository_path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(live).hexdigest() != entry["normalized_text_sha256"]:
            raise ValueError("BASELINE_DRIFT:" + entry["repository_path"])
    if (GOV / "active_governance.json").exists():
        raise ValueError("ALREADY_ADOPTED")
    if not args.apply:
        print("PASS: local authority inputs match; no files changed")
        return
    with (ADAPTER / "candidate/task_registry.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    with REGISTRY.open(encoding="utf-8-sig", newline="") as f:
        validate_preserved_rows(rows, list(csv.DictReader(f)))
    base_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    for row in rows:
        if row["task_id"].startswith("U12-"):
            original = row["acceptance_criteria"]
            row["acceptance_criteria"] = (
                "AC1按冻结输入完成交付，版本与来源可追溯；AC2" + original +
                "；AC3证据与提交绑定，经独立复核及真实第二人签收，不代签外部条件")
            row["evidence_required"] = "输入与交付哈希;专项验证或外部回执;独立复核记录"
            row["reviewer"] = ""
        if row["task_id"] == "U12-01":
            row.update(status="IN_PROGRESS", claimant="Codex", branch="codex/u12-01-governance-migration")
        if row["task_id"] == "W-04":
            row["depends_on"] += "|U12-12"
    with REGISTRY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for source, target in (("release_routes.json", "release_routes_v1.2.json"),
                           ("task_milestones.json", "task_milestones_v1.2.json")):
        value = read(ADAPTER / "candidate" / source)
        if source == "task_milestones.json":
            for milestone in value["milestones"]:
                if milestone["id"] == "A-03-CAL":
                    milestone["consumers"] = ["G-03", "U12-11"]
        write(GOV / "audit_upgrade" / target, value)
    p = read(ADAPTER / "candidate/protocol_authority_v1.2.json")
    p.update(adoption_status="GOVERNANCE_ADOPTED_IMPLEMENTATION_IN_PROGRESS",
             status="DESIGN_CANDIDATE_NOT_PREREGISTERED")
    write(PLAN / "00_总控/protocol_authority_v1.2.json", p)
    write(HERE / "study_manifest_v1.2.template.json", read(ADAPTER / "candidate/study_manifest_v1.2.template.json"))
    write(GOV / "active_governance.json", {
        "version": "1.2", "task": "U12-01", "base_commit": base_commit,
        "research_authority": "../00_总控/protocol_authority_v1.2.json",
        "formal_collection_allowed": False, "runtime_migration_task": "U12-06",
        "legacy_contracts_remain_historical": True,
    })
    mapping = read(GOV / "12_独立任务包文件映射_v1.0.json")
    sources = ["candidate/protocol_authority_v1.2.json", "candidate/task_registry.csv",
               "candidate/task_changes.json", "candidate/release_routes.json", "candidate/task_milestones.json",
               "source_manifest.json", "升级前收尾.md"]
    mapping["tasks"]["U12-01"] = {
        "implementation_commit": base_commit,
        "source_files": [(ADAPTER / name).relative_to(REPO).as_posix() for name in sources],
        "working_paths": [GOV.relative_to(REPO).as_posix(), (PLAN / "00_总控").relative_to(REPO).as_posix(),
                          "Tools/Governance", "04-成果与交付/PDF简报"],
    }
    write(GOV / "12_独立任务包文件映射_v1.0.json", mapping)
    write(HERE / "adoption_record.json", {
        "status": "IMPLEMENTATION_IN_PROGRESS", "base_commit": base_commit,
        "source_adaptation_commit": "703ca504bd3c5da0b61327be5c74909f999e5d2e",
        "old_count": 59, "new_count": 71, "preserved_done": 18,
        "changes": "candidate fields adopted; U12 acceptance made explicit; W-04 consumes U12-12",
        "human_signoff": None, "research_authorized": False,
    })
    print("APPLIED: governance 1.2; U12-01 IN_PROGRESS; research remains blocked")


if __name__ == "__main__":
    main()
