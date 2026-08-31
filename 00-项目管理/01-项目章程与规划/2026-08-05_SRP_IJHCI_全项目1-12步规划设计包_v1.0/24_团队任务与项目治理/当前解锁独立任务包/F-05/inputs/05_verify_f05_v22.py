"""Verify F-05 v2.2 contract artifacts without starting runtime consumers."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


CLAIM_BASE = "cc0b1afe6f71990e6835f74a398bbede4f22f323"
CONTRACT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CONTRACT_ROOT.parents[2]
MODULE_ROOT = REPO_ROOT / "02-技术研发"
V21_PATHS = (
    "02-技术研发/05-通信协议/runtime_contract.py",
    "02-技术研发/05-通信协议/contracts/runtime-contract-v2.1.schema.json",
    "02-技术研发/05-通信协议/contracts/fixtures",
    "02-技术研发/05-通信协议/contracts/fixture_hashes.sha256",
)


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _verify_hash_manifest() -> int:
    manifest = CONTRACT_ROOT / "fixture_hashes_v2.2.sha256"
    count = 0
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative_path = line.split("  ", 1)
        actual = sha256(_canonical_bytes(CONTRACT_ROOT / relative_path)).hexdigest()
        if actual != expected:
            raise RuntimeError(f"F05_HASH_MISMATCH:{relative_path}")
        count += 1
    if count == 0:
        raise RuntimeError("F05_HASH_MANIFEST_EMPTY")
    return count


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _verify_consumers() -> int:
    if str(MODULE_ROOT) not in sys.path:
        sys.path.insert(0, str(MODULE_ROOT))
    from srp_session_core.contract_adapter import validate_message

    root = CONTRACT_ROOT / "consumer-fixtures" / "v2.2"
    unity = _read_jsonl(root / "unity" / "phase-instance-stream.jsonl")
    td = _read_jsonl(root / "touchdesigner" / "phase-instance-stream.jsonl")
    if unity != td or len(unity) != 5:
        raise RuntimeError("F05_CONSUMER_FIXTURE_MISMATCH")
    for frame in unity:
        if validate_message("telemetry_frame", frame) != frame:
            raise RuntimeError("F05_CONSUMER_FIXTURE_FILTERED")
    steps = {(frame["module_id"], frame["target_step_id"]) for frame in unity}
    if {("storm", "hold_1"), ("storm", "hold_2"), ("fade", "inhale_1"), ("fade", "inhale_2")} - steps:
        raise RuntimeError("F05_INSTANCE_FIXTURE_MISSING")
    return len(unity)


def _verify_schema_rebuild() -> None:
    namespace = __import__("runpy").run_path(
        str(CONTRACT_ROOT / "generate_runtime_contract_v22_schema.py")
    )
    expected = namespace["build"]()
    actual = json.loads(
        (CONTRACT_ROOT / "runtime-contract-v2.2.schema.json").read_text(encoding="utf-8")
    )
    if expected != actual:
        raise RuntimeError("F05_SCHEMA_REBUILD_MISMATCH")


def _verify_v21_unchanged() -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", CLAIM_BASE, "--", *V21_PATHS],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("F05_V21_MUTATED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    _verify_v21_unchanged()
    _verify_schema_rebuild()
    report = {
        "report_version": "f05-v22-verification-v1",
        "claim_base": CLAIM_BASE,
        "v21_unchanged": True,
        "schema_rebuild": True,
        "fixture_hash_count": _verify_hash_manifest(),
        "consumer_frame_count": _verify_consumers(),
        "result": "PASS",
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report is not None:
        args.report.write_text(encoded, encoding="utf-8", newline="\n")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
