from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3_corridor样片配置_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3_corridor候选清单_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
H2_REVIEW = HERE / "V-04_H2人工评审记录_v1.0.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stream(probe: dict[str, object], kind: str) -> dict[str, object]:
    matches = [item for item in probe["streams"] if item.get("codec_type") == kind]
    require(len(matches) == 1, f"expected one {kind} stream")
    return matches[0]


def validate_video(entry: dict[str, object], root: Path, expected_size: tuple[int, int]) -> Path:
    path = root / entry["file"]
    require(path.is_file(), f"video missing: {path}")
    require(path.stat().st_size == entry["size_bytes"] and sha256(path) == entry["sha256"], f"video drift: {path.name}")
    video = stream(entry["ffprobe"], "video")
    audio = stream(entry["ffprobe"], "audio")
    require((video.get("width"), video.get("height")) == expected_size, f"video size drift: {path.name}")
    require(video.get("codec_name") == "h264" and video.get("pix_fmt") == "yuv420p", f"video codec drift: {path.name}")
    require(audio.get("codec_name") == "aac" and audio.get("sample_rate") == "48000", f"video audio drift: {path.name}")
    require(int(video.get("nb_frames", 0)) == 360, f"video frame count drift: {path.name}")
    return path


def validate_media_health(ffmpeg: Path, path: Path, maximum_duplicate_run: int) -> None:
    black = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-i", str(path), "-vf", "blackdetect=d=0.10:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require("black_start" not in black.stderr, f"black frame detected: {path.name}")
    hashes = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-f", "framemd5", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    frame_hashes = [line.rsplit(",", 1)[-1].strip() for line in hashes.stdout.splitlines() if line and not line.startswith("#")]
    require(len(frame_hashes) == 360, f"decoded frame count drift: {path.name}")
    max_run = 1
    run = 1
    for previous, current in zip(frame_hashes, frame_hashes[1:]):
        run = run + 1 if current == previous else 1
        max_run = max(max_run, run)
    require(max_run <= maximum_duplicate_run, f"exact frame freeze detected: {path.name}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    require(manifest["preview_id"] == "corridor-candidate-v1" and manifest["technical_id"] == "corridor", "manifest identity drift")
    require(manifest["config_sha256"] == sha256(CONFIG_PATH), "config hash drift")
    require(manifest["design_contract_sha256"] == sha256(HERE / config["design_contract"]), "design contract hash drift")
    require(manifest["h1_selection_sha256"] == sha256(H1_SELECTION), "H1 selection hash drift")
    require(manifest["h2_review_sha256"] == sha256(H2_REVIEW), "H2 review hash drift")
    for role, entry in manifest["sources"].items():
        source = REPO / entry["file"]
        require(source.is_file() and sha256(source) == entry["sha256"], f"{role} source drift")

    render = manifest["render"]
    require(render["duration_s"] == 12.0 and render["fps"] == 30 and render["frame_count"] == 360, "corridor timing drift")
    require(render["sample_is_time_compressed"] is True, "sample must remain explicitly compressed")
    require(render["runtime_candidate_duration_s"] == [20.0, 30.0], "runtime candidate range drift")
    require(render["stage_ratios"] == [0.3, 0.4, 0.3], "transition ratio drift")
    require(render["cue_layers"] == [] and render["audio_phase_inputs"] == [], "transition must not consume cue or phase inputs")
    require(render["condition_pixel_policy"] == "EXACT_IDENTITY", "condition parity policy drift")
    require(render["max_condition_pixel_difference"] == 0, "condition pixel difference detected")
    require(render["condition_video_hashes_identical"] is True, "condition videos are not identical")
    require(render["next_weight_before_reveal"] == 0.0, "next baseline leaked before 0.70")
    require(render["current_weight_after_exit"] == 0.0, "current baseline remained after 0.30")
    require(render["weights"]["at_start"] == [1.0, 0.0, 0.0], "start weights drift")
    require(render["weights"]["at_midpoint"] == [0.0, 1.0, 0.0], "midpoint must be neutral corridor")
    require(render["weights"]["at_end"] == [0.0, 0.0, 1.0], "end weights drift")
    require(render["corridor_stele_travel_px"] >= config["machine_gates"]["minimum_stele_travel_px"], "stele travel is too small")

    root = REPO / config["outputs"]["artifact_root"]
    outputs = manifest["outputs"]
    scene = validate_video(outputs["scene_native"], root, (1920, 1080))
    abstract = validate_video(outputs["abstract_pacer"], root, (1920, 1080))
    validate_video(outputs["paired_review"], root, (3840, 1200))
    require(sha256(scene) == sha256(abstract), "condition media hashes differ")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    maximum_duplicate_run = int(config["machine_gates"]["maximum_exact_duplicate_run_frames"])
    validate_media_health(ffmpeg, scene, maximum_duplicate_run)

    ambient_entry = outputs["ambient_audio"]
    ambient = root / ambient_entry["file"]
    require(ambient.is_file() and sha256(ambient) == ambient_entry["sha256"], "transition audio drift")
    audio = stream(ambient_entry["ffprobe"], "audio")
    require(audio.get("codec_name") == "pcm_s24le", "transition audio must be PCM 24-bit")
    require(audio.get("sample_rate") == "48000" and audio.get("channels") == 2, "transition audio format drift")
    loudness = manifest["audio_metrics"]
    low, high = config["audio"]["integrated_lufs_i"]
    require(low <= loudness["integrated_lufs_i"] <= high, "transition loudness drift")
    require(loudness["true_peak_dbtp"] <= config["audio"]["true_peak_max_dbtp"], "transition true peak drift")

    for key in ("review_keyframes", "grayscale_keyframes"):
        entry = outputs[key]
        path = HERE / entry["file"]
        require(path.is_file() and sha256(path) == entry["sha256"], f"{key} drift")
        with Image.open(path) as image:
            require(image.size == (1920, 1100), f"{key} size drift")

    require(manifest["asset_status"] == {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False}, "asset status drift")
    print(
        "PASS: V-04 corridor-candidate-v1 machine gate; 12s 30/40/30 transition, "
        "exact condition parity, no cue layers, neutral corridor, no next-baseline leak and shared audio verified"
    )


if __name__ == "__main__":
    main()
