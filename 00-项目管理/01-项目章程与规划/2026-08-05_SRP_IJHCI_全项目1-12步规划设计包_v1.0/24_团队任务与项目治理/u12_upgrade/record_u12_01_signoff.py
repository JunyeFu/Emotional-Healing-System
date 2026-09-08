"""Apply the explicit 2026-09-08 human acceptance and unlock direct successors."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOV = HERE.parent
PLAN = GOV.parent
REPO = GOV.parents[3]
CANDIDATE = "47c81744884ae380e047cafb722aeb332c8cda29"
SIGNATURE = "8d75f1a97e91d9d6588d4cccf4492ab73e716826"
SUCCESSORS = ("Q-01", "U12-02", "U12-03", "U12-04", "U12-06", "U12-07")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    registry = GOV / "05_可领取任务包.csv"
    with registry.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["task_id"]: r for r in rows}
    already_signed = (HERE / "acceptance/U12-01.json").is_file() and read(HERE / "acceptance/U12-01.json").get("signature_commit") == SIGNATURE
    if by_id["U12-01"]["status"] != "IN_REVIEW" and not (by_id["U12-01"]["status"] == "DONE" and already_signed):
        raise ValueError("EXPECTED_IN_REVIEW")
    for task in SUCCESSORS:
        if by_id[task]["status"] != "WAIT_DEP" and not (already_signed and by_id[task]["status"] == "READY"):
            raise ValueError("UNEXPECTED_SUCCESSOR_STATE:" + task)
        for dep in by_id[task]["depends_on"].split("|"):
            if dep != "U12-01" and by_id[dep]["status"] != "DONE":
                raise ValueError("INCOMPLETE_DEPENDENCY:" + dep)
    acceptance = {"task_id": "U12-01", "candidate_commit": CANDIDATE,
                  "signature_commit": SIGNATURE, "date": "2026-09-08 +08:00"}
    for key, name, reviewer, role in (
        ("independent_review", "U12-01_独立复核记录.md", "Pascal", "INDEPENDENT_AGENT"),
        ("human_review", "U12-01_第二人审核报告_已签署.md", "傅钧烨", "HUMAN_SECOND_REVIEWER"),
    ):
        path = HERE / name
        acceptance[key] = {"status": "PASS", "reviewer": reviewer, "role": role,
                           "report_path": path.relative_to(REPO).as_posix(),
                           "sha256_lf": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()}
    write(HERE / "acceptance/U12-01.json", acceptance)
    by_id["U12-01"].update(status="DONE", reviewer="傅钧烨")
    for task in SUCCESSORS:
        by_id[task]["status"] = "READY"
    mapping_path = GOV / "12_独立任务包文件映射_v1.0.json"
    mapping = read(mapping_path)
    mapping["tasks"].pop("U12-01", None)
    common = [PLAN / "00_总控/protocol_authority_v1.2.json", HERE / "consumers.json",
              HERE / "study_manifest_v1.2.template.json", GOV / "audit_upgrade/release_routes_v1.2.json",
              GOV / "audit_upgrade/task_milestones_v1.2.json"]
    adapter = PLAN.parent / "2026-09-08_SRP_v1.2_当前基线适配包"
    for task in SUCCESSORS:
        sources = common + ([adapter / "tasks" / task / "inputs/task_input.json"] if task != "Q-01" else [
            PLAN / "20_产品与场景设计/R-01_四层表示方案/R-01_四层候选语法与完整表示方案_v0.9-candidate.md"])
        for entry in read(HERE / "consumers.json")["entries"]:
            if entry["owner"] == task:
                sources.append((PLAN if entry["root"] == "plan" else REPO) / entry["path"])
        mapping["tasks"][task] = {
            "source_files": list(dict.fromkeys(p.relative_to(REPO).as_posix() for p in sources)),
            "working_paths": [PLAN.relative_to(REPO).as_posix(), "02-技术研发"] if task in {"U12-02", "U12-04", "U12-06"}
                             else [PLAN.relative_to(REPO).as_posix()],
        }
    write(mapping_path, mapping)
    record = read(HERE / "adoption_record.json")
    record.update(status="DONE", human_signoff=acceptance["human_review"],
                  signature_commit=SIGNATURE)
    write(HERE / "adoption_record.json", record)
    authority_path = PLAN / "00_总控/protocol_authority_v1.2.json"
    authority = read(authority_path)
    authority["adoption_status"] = "GOVERNANCE_ACCEPTED"
    write(authority_path, authority)
    with registry.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("DONE U12-01; READY " + ",".join(SUCCESSORS))


if __name__ == "__main__":
    main()
