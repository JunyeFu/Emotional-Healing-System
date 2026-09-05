"""Validate READY/IN_REVIEW package coverage, snapshots and hashes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[3]
REGISTRY = ROOT / "05_可领取任务包.csv"
MAPPING = ROOT / "12_独立任务包文件映射_v1.0.json"
OUTPUT = ROOT / "当前解锁独立任务包"
TEXT_SUFFIXES = {
    ".cs", ".csv", ".gitattributes", ".json", ".md", ".ps1", ".py", ".sha256", ".txt"
}
TEXT_NAMES = {".gitattributes"}
PACKAGE_STATUSES = {"READY", "IN_PROGRESS", "IN_REVIEW"}


def canonical_content(path: pathlib.Path) -> bytes:
    content = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in TEXT_NAMES:
        content = content.replace(b"\r\n", b"\n")
        content = b"\n".join(line.rstrip(b" \t") for line in content.split(b"\n"))
    return content


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(canonical_content(path)).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-index", action="store_true",
        help="also require every generated package file to be present in the Git index",
    )
    args = parser.parse_args()
    errors: list[str] = []
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    package_rows = {
        row["task_id"]: row for row in rows if row["status"] in PACKAGE_STATUSES
    }
    mapping = json.loads(MAPPING.read_text(encoding="utf-8-sig"))
    mapped = mapping.get("tasks", {})

    if set(package_rows) != set(mapped):
        errors.append(f"dispatch {sorted(package_rows)} != mapped {sorted(mapped)}")
    if not OUTPUT.is_dir():
        errors.append("output directory is missing")
        packaged: set[str] = set()
    else:
        packaged = {path.name for path in OUTPUT.iterdir() if path.is_dir()}
    if packaged != set(package_rows):
        errors.append(f"dispatch {sorted(package_rows)} != packaged {sorted(packaged)}")
    if not (OUTPUT / "README.md").is_file():
        errors.append("output README.md is missing")

    registry_hash = sha256(REGISTRY)
    total_snapshots = 0
    for task_id, row in package_rows.items():
        package_dir = OUTPUT / task_id
        task_file = package_dir / "TASK.md"
        files_file = package_dir / "FILES.md"
        manifest_file = package_dir / "package_manifest.json"
        for path in (task_file, files_file, manifest_file):
            if not path.is_file():
                errors.append(f"{task_id}: missing {path.name}")
        if not all(path.is_file() for path in (task_file, files_file, manifest_file)):
            continue

        task_text = task_file.read_text(encoding="utf-8-sig")
        files_text = files_file.read_text(encoding="utf-8-sig")
        for marker in (
            f"# {task_id} {row['title']}",
            "## 领取登记",
            "## 四阶段过程",
            "## 验收要求",
            "## 必需证据",
            "## 完成回填",
        ):
            if marker not in task_text:
                errors.append(f"{task_id}: TASK.md missing {marker!r}")
        for criterion in row["acceptance_criteria"].split("；"):
            if criterion.strip() and criterion.strip() not in task_text:
                errors.append(f"{task_id}: missing acceptance criterion {criterion!r}")

        manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
        if manifest.get("task_id") != task_id or manifest.get("status") != row["status"]:
            errors.append(f"{task_id}: invalid manifest identity")
        if manifest.get("hash_policy") != "sha256_lf_no_trailing_ws_text_v1":
            errors.append(f"{task_id}: invalid hash policy")
        if not isinstance(manifest.get("input_snapshot_id"), str) or not manifest["input_snapshot_id"]:
            errors.append(f"{task_id}: missing input_snapshot_id")
        if manifest.get("registry_sha256") != registry_hash:
            errors.append(f"{task_id}: stale registry hash")
        expected_sources = mapped[task_id]["source_files"]
        actual_sources = [item["source_path"] for item in manifest.get("source_files", [])]
        if actual_sources != expected_sources:
            errors.append(f"{task_id}: source list does not match mapping")
        snapshot_payload = "\n".join(
            f"{item.get('source_path')}:{item.get('sha256')}"
            for item in manifest.get("source_files", [])
        ).encode("utf-8")
        expected_snapshot_id = hashlib.sha256(snapshot_payload).hexdigest().upper()
        if manifest.get("input_snapshot_id") != expected_snapshot_id:
            errors.append(f"{task_id}: input_snapshot_id does not match source manifest")
        if row["status"] in {"IN_PROGRESS", "IN_REVIEW"}:
            if manifest.get("previous_input_snapshot_id") != expected_snapshot_id:
                errors.append(f"{task_id}: active input baseline is missing or changed")
            expected_candidate = mapped[task_id].get("implementation_commit")
            if not expected_candidate or manifest.get("candidate_identity") != expected_candidate:
                errors.append(f"{task_id}: candidate identity does not match mapping")
            elif re.fullmatch(r"[0-9a-fA-F]{40}", expected_candidate) is None:
                errors.append(f"{task_id}: candidate identity is not a full commit SHA")
            else:
                candidate = subprocess.run(
                    ["git", "cat-file", "-e", f"{expected_candidate}^{{commit}}"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    check=False,
                )
                if candidate.returncode != 0:
                    errors.append(f"{task_id}: candidate commit does not exist")

        expected_package_files = {
            "TASK.md", "FILES.md", "package_manifest.json",
            *(item["package_path"] for item in manifest.get("source_files", [])),
        }
        physical_package_files = {
            path.relative_to(package_dir).as_posix()
            for path in package_dir.rglob("*")
            if path.is_file()
        }
        unexpected_generated = {
            item for item in physical_package_files - expected_package_files
            if item.startswith("inputs/")
        }
        missing_package_files = expected_package_files - physical_package_files
        if unexpected_generated or missing_package_files:
            errors.append(
                f"{task_id}: physical package files differ from manifest "
                f"extra_generated={sorted(unexpected_generated)} "
                f"missing={sorted(missing_package_files)}"
            )
        if args.require_index:
            for relative in sorted(physical_package_files):
                project_relative = (package_dir / relative).relative_to(PROJECT_ROOT).as_posix()
                tracked = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", "--", project_relative],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    check=False,
                )
                if tracked.returncode != 0:
                    errors.append(f"{task_id}: package file is not in Git index {relative}")

        for item in manifest.get("source_files", []):
            source = (PROJECT_ROOT / item["source_path"]).resolve()
            snapshot = (package_dir / item["package_path"]).resolve()
            if PROJECT_ROOT not in source.parents or not source.is_file():
                errors.append(f"{task_id}: invalid source {item['source_path']}")
                continue
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", item["source_path"]],
                cwd=PROJECT_ROOT,
                capture_output=True,
                check=False,
            )
            if tracked.returncode != 0:
                errors.append(f"{task_id}: source is not tracked {item['source_path']}")
            if package_dir not in snapshot.parents or not snapshot.is_file():
                errors.append(f"{task_id}: invalid snapshot {item['package_path']}")
                continue
            snapshot_relative = snapshot.relative_to(PROJECT_ROOT).as_posix()
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", "--", snapshot_relative],
                cwd=PROJECT_ROOT,
                capture_output=True,
                check=False,
            )
            if ignored.returncode == 0:
                errors.append(f"{task_id}: snapshot is ignored by Git {item['package_path']}")
            expected_hash = sha256(source)
            if item.get("sha256") != expected_hash or sha256(snapshot) != expected_hash:
                errors.append(f"{task_id}: hash drift {item['source_path']}")
            if item["source_path"] not in files_text or item["package_path"] not in files_text:
                errors.append(f"{task_id}: FILES.md omits {item['source_path']}")
            total_snapshots += 1

        for relative in mapped[task_id]["working_paths"]:
            path = (PROJECT_ROOT / relative).resolve()
            if PROJECT_ROOT not in path.parents or not path.exists():
                errors.append(f"{task_id}: invalid working path {relative}")
            if relative not in files_text:
                errors.append(f"{task_id}: FILES.md omits working path {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        f"PASS: dispatch packages={len(package_rows)}; snapshots={total_snapshots}; "
        f"tasks={','.join(sorted(package_rows))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
