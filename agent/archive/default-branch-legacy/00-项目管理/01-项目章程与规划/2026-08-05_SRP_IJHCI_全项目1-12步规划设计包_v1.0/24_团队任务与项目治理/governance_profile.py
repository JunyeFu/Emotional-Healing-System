"""Resolve an explicit governance version without changing legacy contracts."""
import json
import hashlib
import re
import subprocess
from pathlib import Path


def load_profile(root: Path):
    path = root / "active_governance.json"
    version = json.loads(path.read_text(encoding="utf-8"))["version"] if path.exists() else "1.0"
    if version not in {"1.0", "1.2"}:
        raise ValueError("UNKNOWN_GOVERNANCE_VERSION")
    upgraded = version == "1.2"
    return {
        "version": version,
        "count": 71 if upgraded else 59,
        "fixed": 68 if upgraded else 56,
        "routes": root / "audit_upgrade" / f"release_routes_v{version}.json",
        "milestones": root / "audit_upgrade" / f"task_milestones_v{version}.json",
        "a06_dependencies": "A-05|U12-10" if upgraded else "A-05",
        "w02_dependencies": "W-01|A-06|U12-07" if upgraded else "W-01|A-06",
        "g03_dependencies": "E-03|X-01|Z-01|A-02|A-03-CAL|G-05" + ("|U12-11" if upgraded else ""),
    }


def validate_u12_acceptance(row, incomplete_dependencies, root):
    if not row["task_id"].startswith("U12-") or row["status"] != "DONE":
        return []
    errors = []
    task_id = row["task_id"]
    if incomplete_dependencies:
        errors.append(task_id + ":DONE_WITH_INCOMPLETE_DEPENDENCIES")
    path = root / "u12_upgrade/acceptance" / (task_id + ".json")
    if not path.is_file():
        return errors + [task_id + ":HUMAN_ACCEPTANCE_MISSING"]
    record = json.loads(path.read_text(encoding="utf-8"))
    repo = root.parents[3]
    candidate = record.get("candidate_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", candidate) or subprocess.run(
        ["git", "cat-file", "-e", candidate + "^{commit}"], cwd=repo, capture_output=True
    ).returncode:
        errors.append(task_id + ":INVALID_ACCEPTED_COMMIT")
    if record.get("task_id") != task_id:
        errors.append(task_id + ":ACCEPTANCE_TASK_MISMATCH")
    identities = [str(row.get("claimant", "")).strip().casefold(),
                  str(record.get("independent_review", {}).get("reviewer", "")).strip().casefold(),
                  str(record.get("human_review", {}).get("reviewer", "")).strip().casefold()]
    if any(not identity for identity in identities) or len(set(identities)) != 3:
        errors.append(task_id + ":REVIEWER_SEPARATION_REQUIRED")
    for key in ("independent_review", "human_review"):
        review = record.get(key, {})
        reviewer = review.get("reviewer", "")
        relative = review.get("report_path", "")
        report = (repo / relative).resolve()
        if review.get("status") != "PASS" or not reviewer or not relative or repo not in report.parents or not report.is_file():
            errors.append(task_id + ":INVALID_" + key.upper())
            continue
        if key == "human_review" and (review.get("role") != "HUMAN_SECOND_REVIEWER" or re.search(r"agent|codex|gpt|待|未指定|tbd|pending", reviewer, re.I)):
            errors.append(task_id + ":HUMAN_REVIEWER_REQUIRED")
        content = report.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != review.get("sha256_lf"):
            errors.append(task_id + ":REVIEW_HASH_MISMATCH")
        text = content.decode("utf-8-sig")
        if any(marker not in text for marker in (task_id, candidate, reviewer, "PASS")):
            errors.append(task_id + ":REVIEW_IDENTITY_MISMATCH")
    return errors
