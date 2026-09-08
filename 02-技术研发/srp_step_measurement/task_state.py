"""Maintain U12-02 claim/review metadata without changing frozen inputs."""
import argparse
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("state", choices=["IN_PROGRESS", "IN_REVIEW"])
    p.add_argument("--candidate")
    args = p.parse_args()
    registry = GOV / "05_可领取任务包.csv"
    with registry.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    row = next(r for r in rows if r["task_id"] == "U12-02")
    expected = "READY" if args.state == "IN_PROGRESS" else "IN_PROGRESS"
    if row["status"] != expected and not (args.state == "IN_PROGRESS" and row["status"] == "IN_PROGRESS"):
        raise ValueError("INVALID_TASK_TRANSITION")
    if args.state == "IN_REVIEW" and not args.candidate:
        raise ValueError("REVIEW_REQUIRES_CANDIDATE")
    commit = subprocess.check_output(["git", "rev-parse", "--verify", (args.candidate or "HEAD") + "^{commit}"], cwd=ROOT, text=True).strip()
    path = GOV / "12_独立任务包文件映射_v1.0.json"
    mapping = json.loads(path.read_text(encoding="utf-8"))
    mapping["tasks"]["U12-02"]["implementation_commit"] = commit
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    row.update(status=args.state, claimant="Codex", branch="codex/u12-02-step-measurement",
               reviewer="独立Agent复核；真实第二人签收另记" if args.state == "IN_REVIEW" else "")
    with registry.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("U12-02", args.state)


if __name__ == "__main__":
    main()
