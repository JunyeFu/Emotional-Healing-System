from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3_heat样片配置_v2.0.json"
MANIFEST_PATH = HERE / "V-04_H3_heat候选清单_v2.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
BACKGROUND_SELECTION = HERE / "V-04_H3_R2背景选择记录_v1.0.json"
H2_REVIEW = HERE / "V-04_H2_candidate-v11人工评审记录_v1.0.json"


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
    require(int(video.get("nb_frames", 0)) == 300, f"video frame count drift: {path.name}")
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
    require(len(frame_hashes) == 300, f"decoded frame count drift: {path.name}")
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
    require(manifest["schema_version"] == "2.0", "manifest schema drift")
    require(manifest["preview_id"] == "heat-candidate-v2" and manifest["technical_id"] == "heat", "manifest identity drift")
    require(manifest["config_sha256"] == sha256(CONFIG_PATH), "config hash drift")
    require(manifest["design_contract_sha256"] == sha256(HERE / config["design_contract"]), "design contract hash drift")
    require(manifest["mechanism_contract_sha256"] == sha256(HERE / config["mechanism_contract"]), "mechanism contract hash drift")
    require(manifest["background_selection_sha256"] == sha256(BACKGROUND_SELECTION), "background selection hash drift")
    require(manifest["h2_review_sha256"] == sha256(H2_REVIEW), "H2 review hash drift")
    source = REPO / manifest["source"]["file"]
    require(source.is_file() and sha256(source) == manifest["source"]["sha256"], "heat source drift")

    render = manifest["render"]
    require(render["duration_s"] == 10.0 and render["fps"] == 30 and render["frame_count"] == 300, "heat timing drift")
    require(render["inhale_duration_s"] == 4.0 and render["exhale_duration_s"] == 6.0, "phase duration drift")
    require(render["phase_slots"] == ["INHALE", "EXHALE"], "phase order drift")
    require(render["background_phase_inputs"] == [], "background must not consume phase inputs")
    require(
        render["max_raw_difference_outside_expected_mask"]
        <= config["machine_gates"]["max_raw_difference_outside_expected_mask"],
        "condition difference escaped expected regions",
    )
    require(render["camera_mode"] == "fixed" and render["horizontal_scroll"] is False, "fixed camera contract drift")
    require(render["camera_displacement_px"] == 0.0, "camera displacement must be zero")
    require(render["source_fit"] == "cover_center_crop", "source fit drift")

    geometry = render["geometry_metrics"]
    gates = config["machine_gates"]
    require(geometry["inhale_rise_px"] >= gates["minimum_inhale_rise_px"], "inhale rise is too small")
    require(
        geometry["exhale_forward_travel_px"] >= gates["minimum_exhale_forward_travel_px"],
        "exhale forward travel is too small",
    )
    require(
        geometry["exhale_to_inhale_path_ratio"] >= gates["minimum_exhale_to_inhale_path_ratio"],
        "exhale path is not sufficiently longer than inhale",
    )
    opacity_gain = geometry["exhale_max_opacity"] - geometry["inhale_max_opacity"]
    require(opacity_gain <= gates["maximum_exhale_opacity_gain"], "exhale became brighter than inhale")
    require(geometry["target_at_4s"] == "EXHALE" and geometry["actual_at_4s"] == "INHALE", "divergent 4-second boundary lost")

    root = REPO / config["outputs"]["artifact_root"]
    outputs = manifest["outputs"]
    scene = validate_video(outputs["scene_native"], root, (1920, 1080))
    abstract = validate_video(outputs["abstract_pacer"], root, (1920, 1080))
    validate_video(outputs["paired_review"], root, (3840, 1200))
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    maximum_duplicate_run = int(gates["maximum_exact_duplicate_run_frames"])
    validate_media_health(ffmpeg, scene, maximum_duplicate_run)
    validate_media_health(ffmpeg, abstract, maximum_duplicate_run)

    ambient_entry = outputs["ambient_audio"]
    ambient = root / ambient_entry["file"]
    require(ambient.is_file() and sha256(ambient) == ambient_entry["sha256"], "ambient audio drift")
    audio = stream(ambient_entry["ffprobe"], "audio")
    require(audio.get("codec_name") == "pcm_s24le", "ambient audio must be PCM 24-bit")
    require(audio.get("sample_rate") == "48000" and audio.get("channels") == 2, "ambient audio format drift")
    loudness = manifest["audio_metrics"]
    low, high = config["audio"]["integrated_lufs_i"]
    require(low <= loudness["integrated_lufs_i"] <= high, "ambient loudness drift")
    require(loudness["true_peak_dbtp"] <= config["audio"]["true_peak_max_dbtp"], "ambient true peak drift")

    for key in ("review_keyframes", "grayscale_keyframes"):
        entry = outputs[key]
        path = HERE / entry["file"]
        require(path.is_file() and sha256(path) == entry["sha256"], f"{key} drift")
        with Image.open(path) as image:
            require(image.size == (1920, 1400), f"{key} size drift")

    require(manifest["asset_status"] == {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False}, "asset status drift")
    print(
        "PASS: V-04 heat-candidate-v2 machine gate; 10s 4-6 dual-condition media, "
        "longer exhale path, divergent actual, shared fixed camera, environment and audio verified; human review pending"
    )


if __name__ == "__main__":
    main()
