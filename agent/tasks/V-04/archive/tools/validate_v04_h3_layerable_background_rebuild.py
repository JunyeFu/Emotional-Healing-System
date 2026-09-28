"""Validate the V-04 layerable-background rebuild candidate package."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "AGENTS.md").is_file())
MANIFEST = HERE / "V-04_H3_可拆层背景重建候选清单_v1.0.json"
WEATHERS = {"storm", "heat", "snow", "fade"}
LAYERS = {"sky_clouds", "far_landform_01", "far_landform_02", "far_landform_03", "mid_terrain", "ground_visual", "foreground_occluders"}
ROOTS = {"TargetCueRoot", "ActualFeedbackRoot", "RecoveryStateRoot", "FallbackStateRoot"}
SELECTION = {"storm": "B", "heat": "C", "snow": "C", "fade": "C"}


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("status") != "CANDIDATE_READY_FOR_HUMAN_REVIEW":
        errors.append("unexpected candidate status")
    if manifest.get("current_gate") != "H3_LAYERABLE_BACKGROUND_REBUILD":
        errors.append("unexpected current gate")
    if set(manifest.get("required_static_layers", [])) != LAYERS:
        errors.append("unexpected static layer contract")
    if set(manifest.get("required_semantic_roots", [])) != ROOTS:
        errors.append("unexpected semantic root contract")
    canvas = manifest.get("canvas_contract", {})
    if canvas != {"source_width": 3840, "source_height": 2160, "aspect_ratio": "16:9", "camera": "FIXED", "parallax_scroll": False}:
        errors.append("unexpected canvas contract")
    candidates = manifest.get("candidates", [])
    if len(candidates) != 4 or {candidate.get("weather") for candidate in candidates} != WEATHERS:
        errors.append("candidate coverage must be exactly four weather modules")
    for candidate in candidates:
        weather = candidate.get("weather")
        if candidate.get("selected_direction") != SELECTION.get(weather):
            errors.append(f"unexpected selected direction: {weather}")
        path = ROOT / candidate["base_path"]
        if not path.is_file():
            errors.append(f"missing base image: {weather}")
            continue
        if png_size(path) != (candidate["width"], candidate["height"]):
            errors.append(f"dimension mismatch: {weather}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != candidate["sha256"]:
            errors.append(f"hash mismatch: {weather}")
        if candidate.get("asset_status") != "TEMP_REFERENCE_ONLY" or candidate.get("formal_use_allowed") is not False:
            errors.append(f"unexpected asset boundary: {weather}")
    result = {"validator": Path(__file__).name, "result": "PASS" if not errors else "FAIL", "candidate_count": len(candidates), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
