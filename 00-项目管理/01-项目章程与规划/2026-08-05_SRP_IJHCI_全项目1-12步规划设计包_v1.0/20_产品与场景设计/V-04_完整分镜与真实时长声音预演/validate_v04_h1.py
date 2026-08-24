from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
MANIFEST = HERE / "V-04_H1候选清单_v1.0.json"
REVIEW_REPORT = HERE / "V-04_H1评审图清单_v1.0.json"
STATUS_RECORD = HERE / "V-04_实施状态与H1确认记录_v1.0.md"
SOURCE = REPO / ".artifacts-local" / "V-04" / "H1" / "candidates"

SCENES = ("storm", "heat", "snow", "fade", "corridor")
VARIANTS = ("A", "B")
EXPECTED_SIZE = (1672, 941)
EXPECTED_REVIEW_SIZE = (1920, 650)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = json.loads(REVIEW_REPORT.read_text(encoding="utf-8"))
    candidates = manifest.get("candidates", [])

    require(manifest.get("task_id") == "V-04", "manifest task_id must be V-04")
    require(manifest.get("gate_id") == "H1", "manifest gate_id must be H1")
    require(
        manifest.get("gate_status") == "PENDING_HUMAN_CONFIRMATION",
        "H1 must remain pending until the team director selects five anchors",
    )
    require(len(candidates) == 10, "H1 must contain exactly ten candidates")
    require(
        Counter(item.get("scene_id") for item in candidates) == Counter({scene: 2 for scene in SCENES}),
        "each scene must contain exactly two candidates",
    )
    require(
        {(item.get("scene_id"), item.get("variant")) for item in candidates}
        == {(scene, variant) for scene in SCENES for variant in VARIANTS},
        "candidate scene/variant matrix must be five scenes by A/B",
    )

    for item in candidates:
        candidate_id = str(item["candidate_id"])
        source = SOURCE / str(item["file"])
        require(source.is_file(), f"candidate is missing: {candidate_id}")
        require(sha256(source) == item.get("sha256"), f"candidate hash mismatch: {candidate_id}")
        require(source.stat().st_size == item.get("size_bytes"), f"candidate size mismatch: {candidate_id}")
        with Image.open(source) as image:
            require(image.size == EXPECTED_SIZE, f"candidate dimensions mismatch: {candidate_id}")
            require(image.mode == "RGB", f"candidate mode must be RGB: {candidate_id}")
        require(item.get("width") == EXPECTED_SIZE[0], f"manifest width mismatch: {candidate_id}")
        require(item.get("height") == EXPECTED_SIZE[1], f"manifest height mismatch: {candidate_id}")
        require(item.get("mode") == "RGB", f"manifest mode mismatch: {candidate_id}")
        require(item.get("revision") == 2, f"only revision 2 may enter H1 review: {candidate_id}")
        require(bool(item.get("revision_prompt")), f"revision rationale is missing: {candidate_id}")
        require(len(str(item.get("supersedes_sha256", ""))) == 64, f"superseded hash is missing: {candidate_id}")
        require(item.get("status") == "PENDING_H1_SELECTION", f"candidate status drift: {candidate_id}")
        require(item.get("formal_use_allowed") is False, f"candidate cannot be formal-use enabled: {candidate_id}")

    require(report.get("source_manifest_sha256") == sha256(MANIFEST), "review report manifest hash drift")
    require(report.get("selection_status") == "PENDING_HUMAN_CONFIRMATION", "review status must remain pending")
    outputs = report.get("outputs", [])
    require(len(outputs) == 5, "five A/B review sheets are required")
    require({item.get("scene_id") for item in outputs} == set(SCENES), "review sheet scene set drift")
    for item in outputs:
        output = HERE / str(item["file"])
        require(output.is_file(), f"review sheet is missing: {item.get('scene_id')}")
        require(sha256(output) == item.get("sha256"), f"review sheet hash mismatch: {item.get('scene_id')}")
        with Image.open(output) as image:
            require(image.size == EXPECTED_REVIEW_SIZE, f"review dimensions mismatch: {item.get('scene_id')}")
            require(image.mode == "RGB", f"review sheet mode must be RGB: {item.get('scene_id')}")
        require(item.get("review_overlay_only") is True, "review guides must not be presented as source art")

    ignored = git_lines("check-ignore", "--", str(SOURCE.relative_to(REPO)).replace("\\", "/"))
    require(bool(ignored), "candidate source directory must remain ignored by Git")
    tracked_local = git_lines("ls-files", "--", ".artifacts-local", ".tools")
    require(not tracked_local, "local source assets or tools must not be tracked")
    local_files = [path for path in (REPO / ".artifacts-local" / "V-04").rglob("*") if path.is_file()]
    require(
        all(path.suffix.lower() in {".png", ".mp4"} for path in local_files),
        "unexpected generated artifact type exists before H1 selection",
    )

    status_text = STATUS_RECORD.read_text(encoding="utf-8")
    require("H1候选生成：`READY_FOR_HUMAN_REVIEW`" in status_text, "status record is not review-ready")
    require("H1团队总监确认：`PENDING_HUMAN_CONFIRMATION`" in status_text, "human gate status drift")
    require("H2及后续：`BLOCKED_BY_H1`" in status_text, "H2 must remain blocked")

    print(
        "PASS: V-04 H1 candidate set verified; 10 source images and 5 review sheets exact; "
        "formal use disabled; human selection still pending"
    )


if __name__ == "__main__":
    main()
