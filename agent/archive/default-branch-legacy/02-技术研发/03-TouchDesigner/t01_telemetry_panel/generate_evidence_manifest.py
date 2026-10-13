"""Generate deterministic hashes for the T-01 runtime artifacts and evidence."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT = BASE_DIR / "evidence" / "evidence_manifest.json"
INCLUDE = (
    "T01_TelemetryPanel.toe",
    "T01_TelemetryPanel.tox",
    "evidence/host/field_manifest.json",
    "evidence/host/host_build_manifest.json",
    "evidence/host/node_permissions.json",
    "evidence/host/node_plan.json",
    "evidence/touchdesigner/capture_manifest.json",
    "evidence/touchdesigner/node_errors.json",
    "evidence/touchdesigner/node_inventory.json",
    "evidence/touchdesigner/reopen_report.json",
    "evidence/touchdesigner/runtime_build_manifest.json",
    "evidence/touchdesigner/screenshots/disconnected.png",
    "evidence/touchdesigner/screenshots/fixture_good.png",
    "evidence/touchdesigner/screenshots/out_of_order.png",
    "evidence/touchdesigner/screenshots/publisher_live.png",
    "evidence/touchdesigner/screenshots/recovered.png",
    "evidence/touchdesigner/states/disconnected.json",
    "evidence/touchdesigner/states/fixture_good.json",
    "evidence/touchdesigner/states/out_of_order.json",
    "evidence/touchdesigner/states/publisher_live.json",
    "evidence/touchdesigner/states/recovered.json",
    "evidence/touchdesigner/video/fixture_replay.ffconcat",
    "evidence/touchdesigner/video/fixture_replay.mp4",
)


def main() -> None:
    artifacts = {}
    for relative in INCLUDE:
        path = BASE_DIR / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        artifacts[relative] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path.read_bytes()).hexdigest().upper(),
        }
    report = {
        "manifest_schema_version": "t01-evidence-manifest-v1",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "evidence_boundary": "LOCAL_TD_RUNTIME_NOT_LIVE_E2E",
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"T01_EVIDENCE_MANIFEST_COMPLETE {len(artifacts)} artifacts")


if __name__ == "__main__":
    main()
