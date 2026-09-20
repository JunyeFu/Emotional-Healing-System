"""U12-04 evidence builder: hash sources + outputs and write evidence.json.

Hash policy: sha256_lf_no_trailing_ws_text_v1
  read utf-8-sig -> split lines -> rstrip each -> join "\n" + trailing "\n"
  -> sha256 hex uppercase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
PACKAGE_ROOT = HERE.parents[2]
# Input snapshot manifest (source_files + input_snapshot_id) lives in the v1.0
# package's unlocked-task registry.
MANIFEST = (
    PACKAGE_ROOT
    / "24_团队任务与项目治理"
    / "当前解锁独立任务包"
    / "U12-04"
    / "package_manifest.json"
)
# Execution registry (task_input.json with base_commit) lives in the v1.2 package.
TASK_INPUT = (
    HERE.parents[3]
    / "2026-09-08_SRP_v1.2_当前基线适配包"
    / "tasks"
    / "U12-04"
    / "inputs"
    / "task_input.json"
)
EVIDENCE = HERE / "evidence.json"

OUTPUT_FILES = (
    "sap.md",
    "contract.json",
    "power_spec.json",
    "power_simulation.py",
    "sources.md",
    "validate.py",
    "test_contract.py",
    "build_evidence.py",
    "README.md",
)


def text_hash(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8-sig")
    lines = [line.rstrip() for line in text.split("\n")]
    if lines and lines[-1] == "":
        lines = lines[:-1]
    normalized = "\n".join(lines) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def load_baseline_commit() -> str | None:
    if not TASK_INPUT.exists():
        return None
    data = json.loads(TASK_INPUT.read_text(encoding="utf-8"))
    return data.get("base_commit") or data.get("baseline_commit")


def build_evidence() -> dict:
    manifest = load_manifest()
    snapshot = manifest["input_snapshot_id"]

    sources = []
    for entry in manifest.get("source_files", []):
        name = entry.get("name") or entry.get("file") or str(entry.get("source_path", ""))
        declared = entry.get("sha256", "")
        candidate = ROOT / (entry.get("source_path", "") or "")
        recomputed = text_hash(candidate) if candidate.exists() else None
        sources.append(
            {
                "name": name,
                "sha256_declared": declared,
                "sha256_recomputed": recomputed,
                "verified": bool(recomputed and recomputed == declared),
            }
        )

    outputs = []
    for name in OUTPUT_FILES:
        path = HERE / name
        if not path.exists():
            raise SystemExit(f"missing output: {path}")
        outputs.append({"name": name, "sha256": text_hash(path)})

    return {
        "schema_version": "1.0",
        "evidence_class": "DESIGN_AND_SYNTHETIC_ONLY",
        "evidence_status": "DESIGN_AND_SYNTHETIC_ONLY",
        "hash_policy": "UTF8_LF_TRAILING_WHITESPACE_REMOVED_FINAL_LF",
        "input_snapshot_id": snapshot,
        "baseline_commit": load_baseline_commit(),
        "sources": sources,
        "outputs": outputs,
        "real_clips": "PENDING",
        "participant_observations": "PENDING",
        "research_freeze": "PENDING",
    }


def check(existing: dict, fresh: dict) -> bool:
    return existing.get("input_snapshot_id") == fresh["input_snapshot_id"] and (
        existing.get("sources") == fresh["sources"]
        and existing.get("outputs") == fresh["outputs"]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="U12-04 evidence builder")
    parser.add_argument("--check", action="store_true", help="verify existing evidence.json")
    parser.add_argument("--output", default=str(EVIDENCE), help="output path")
    args = parser.parse_args()

    fresh = build_evidence()
    out = Path(args.output)

    if args.check:
        if not out.exists():
            raise SystemExit("evidence.json missing")
        existing = json.loads(out.read_text(encoding="utf-8"))
        if not check(existing, fresh):
            raise SystemExit("EVIDENCE_MISMATCH")
        print("EVIDENCE_OK")
        return

    out.write_text(
        json.dumps(fresh, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    unverified = [s["name"] for s in fresh["sources"] if not s["verified"]]
    if unverified:
        print("EVIDENCE_WRITTEN_WITH_UNVERIFIED_SOURCES: " + ", ".join(unverified))
    else:
        print("EVIDENCE_OK")


if __name__ == "__main__":
    main()
