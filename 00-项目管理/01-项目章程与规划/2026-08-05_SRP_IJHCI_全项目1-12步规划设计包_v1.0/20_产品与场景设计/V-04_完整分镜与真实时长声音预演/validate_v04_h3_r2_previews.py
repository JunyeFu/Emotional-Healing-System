"""Validate the V-04 R2 fixed-camera deep-scene preview manifest."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "AGENTS.md").is_file())
MANIFEST = HERE / "V-04_H3_R2大景深背景预览候选清单_v1.0.json"
WEATHERS = {"storm", "heat", "snow", "fade"}
GROUPS = {"A", "B", "C"}


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    candidates = manifest.get("candidates", [])
    if len(candidates) != 12:
        errors.append(f"expected 12 candidates, got {len(candidates)}")
    if manifest.get("current_gate") != "H3_FIXED_BACKGROUND_PREVIEW_SELECTION":
        errors.append("unexpected current gate")
    camera = manifest.get("camera_contract", {})
    if any(camera.get(weather) != "FIXED" for weather in WEATHERS):
        errors.append("all weather cameras must be FIXED")
    if camera.get("camera_translation") != 0 or camera.get("background_translation") != 0:
        errors.append("camera and background translation must be zero")
    if camera.get("parallax_scroll") is not False:
        errors.append("parallax scroll must be false")

    pairs = {(candidate.get("group"), candidate.get("weather")) for candidate in candidates}
    expected_pairs = {(group, weather) for group in GROUPS for weather in WEATHERS}
    if pairs != expected_pairs:
        errors.append("candidate groups must cover every weather exactly once")

    for candidate in candidates:
        path = ROOT / candidate["path"]
        if not path.is_file():
            errors.append(f"missing preview: {candidate['candidate_id']}")
            continue
        width, height = png_size(path)
        if (width, height) != (candidate["width"], candidate["height"]):
            errors.append(f"dimension mismatch: {candidate['candidate_id']}")
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != candidate["sha256"]:
            errors.append(f"hash mismatch: {candidate['candidate_id']}")
        if candidate.get("asset_status") != "TEMP_REFERENCE_ONLY":
            errors.append(f"unexpected asset status: {candidate['candidate_id']}")
        if candidate.get("formal_use_allowed") is not False:
            errors.append(f"formal use must remain false: {candidate['candidate_id']}")

    result = {
        "validator": Path(__file__).name,
        "result": "PASS" if not errors else "FAIL",
        "candidate_count": len(candidates),
        "groups": sorted(GROUPS),
        "weathers": sorted(WEATHERS),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
