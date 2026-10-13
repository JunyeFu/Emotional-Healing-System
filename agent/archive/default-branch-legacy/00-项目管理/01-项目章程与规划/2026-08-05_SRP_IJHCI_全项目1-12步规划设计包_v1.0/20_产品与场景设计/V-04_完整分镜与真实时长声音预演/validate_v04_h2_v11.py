from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H2样片配置_v1.4.json"
MANIFEST_PATH = HERE / "V-04_H2候选清单_v1.4.json"
CONTRACT_PATH = HERE / "V-04_H2_candidate-v11_固定底片样片合同_v1.0.md"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
BACKGROUND_SELECTION = HERE / "V-04_H2固定底片选择记录_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def stream(probe: dict[str, object], kind: str) -> dict[str, object]:
    matches = [item for item in probe["streams"] if item.get("codec_type") == kind]
    require(len(matches) == 1, f"expected one {kind} stream")
    return matches[0]


def validate_video(entry: dict[str, object], root: Path, size: tuple[int, int]) -> None:
    path = root / entry["file"]
    require(path.is_file(), f"video missing: {entry['file']}")
    require(path.stat().st_size == entry["size_bytes"], f"video size drift: {entry['file']}")
    require(sha256(path) == entry["sha256"], f"video hash drift: {entry['file']}")
    probe = entry["ffprobe"]
    require(probe["format"].get("filename") == entry["file"], f"unstable probe path: {entry['file']}")
    video = stream(probe, "video")
    audio = stream(probe, "audio")
    require(video.get("codec_name") == "h264", f"video codec drift: {entry['file']}")
    require((video.get("width"), video.get("height")) == size, f"video size drift: {entry['file']}")
    require(video.get("pix_fmt") == "yuv420p", f"pixel format drift: {entry['file']}")
    require(video.get("nb_frames") == "300", f"frame count drift: {entry['file']}")
    require(audio.get("codec_name") == "aac", f"audio codec drift: {entry['file']}")
    require(audio.get("sample_rate") == "48000" and audio.get("channels") == 2, f"audio drift: {entry['file']}")
    require(abs(float(probe["format"]["duration"]) - 10.0) <= 0.06, f"duration drift: {entry['file']}")


def validate_sheet(entry: dict[str, object], expected_name: str) -> None:
    path = HERE / entry["file"]
    require(path.name == expected_name, f"review sheet name drift: {entry['file']}")
    require(path.is_file(), f"review sheet missing: {entry['file']}")
    require(path.stat().st_size == entry["size_bytes"], f"review sheet size drift: {entry['file']}")
    require(sha256(path) == entry["sha256"], f"review sheet hash drift: {entry['file']}")
    with Image.open(path) as image:
        require(image.size == (1920, 1590) and image.mode == "RGB", f"review sheet format drift: {entry['file']}")


def validate_fixed_camera_media_health(ffmpeg: Path, path: Path) -> None:
    black = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            "blackdetect=d=0.10:pix_th=0.10",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    require("black_start" not in black.stderr, f"black frame detected: {path.name}")
    hashes = subprocess.run(
        [str(ffmpeg), "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "framemd5", "-"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    frame_hashes = [line.rsplit(",", 1)[-1].strip() for line in hashes.stdout.splitlines() if re.match(r"\s*0,", line)]
    require(len(frame_hashes) == 300, f"decoded frame count drift: {path.name}")
    max_run = 0
    run = 0
    previous = None
    for frame_hash in frame_hashes:
        run = run + 1 if frame_hash == previous else 1
        previous = frame_hash
        max_run = max(max_run, run)
    require(max_run < 30, f"one-second exact frame freeze detected: {path.name}")


def validate_geometry(metrics: dict[str, object], gates: dict[str, object]) -> None:
    require(metrics["target_alpha_outside_water_max"] <= gates["target_alpha_outside_water_max"], "target escaped water")
    require(metrics["actual_alpha_outside_water_max"] <= gates["actual_alpha_outside_water_max"], "actual escaped water")
    require(metrics["inhale_1_area_px"] >= gates["inhale_1_min_area_px"], "first inhale area too small")
    require(metrics["inhale_2_retained_ratio"] >= gates["inhale_2_retained_ratio_min"], "supplement reset main tide")
    require(metrics["inhale_2_added_area_px"] >= gates["inhale_2_added_area_px_min"], "supplement is not distinct")
    require(metrics["inhale_2_area_ratio"] <= gates["inhale_2_area_ratio_max"], "supplement is too large")
    require(metrics["exhale_head_travel_px"] >= gates["exhale_head_travel_px_min"], "exhale travel too short")
    require(
        metrics["exhale_centroid_downstream_px"] >= gates["exhale_centroid_downstream_px_min"],
        "exhale centroid did not move downstream",
    )
    require(metrics["end_residual_area_ratio"] <= gates["end_residual_area_ratio_max"], "target left a permanent trace")
    require(
        min(metrics["grayscale_mean_delta"].values()) >= gates["grayscale_mean_delta_min"],
        "grayscale geometry contrast too low",
    )
    require(metrics["actual_phase_at_target_inhale_2_start"] == "INHALE_1", "actual supplement was inferred")
    require(metrics["actual_phase_after_lag"] == "INHALE_2", "actual supplement missing after lag")
    require(metrics["actual_exhale_phase"] == "EXHALE_1", "actual exhale missing")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    background_selection = json.loads(BACKGROUND_SELECTION.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    require(ffmpeg.is_file(), "locked FFmpeg is missing")
    require(config.get("schema_version") == "1.4", "H2 v11 config schema drift")
    require(config.get("candidate_id") == "candidate-v11", "H2 v11 candidate drift")
    require(manifest.get("schema_version") == "1.4", "H2 v11 manifest schema drift")
    require(manifest.get("candidate_id") == config["candidate_id"], "H2 v11 identity mismatch")
    require(manifest.get("gate_status") == "PENDING_HUMAN_CONFIRMATION", "H2 v11 human gate drift")
    require(manifest.get("config_sha256") == sha256(CONFIG_PATH), "H2 v11 config hash drift")
    require(manifest.get("design_contract_sha256") == sha256(CONTRACT_PATH), "H2 v11 contract hash drift")
    require(manifest.get("h1_selection_sha256") == sha256(H1_SELECTION), "H1 selection hash drift")
    require(
        manifest.get("background_selection_sha256") == sha256(BACKGROUND_SELECTION),
        "background selection hash drift",
    )
    require(any(item["candidate_id"] == "fade-B" for item in h1["selections"]), "fade-B selection missing")
    require(background_selection.get("decision") == "PASS", "background human selection missing")
    require(
        background_selection.get("candidate_id") == config["source"]["selected_anchor_id"],
        "background candidate identity mismatch",
    )
    camera = config.get("camera", {})
    require(camera.get("mode") == "fixed" and camera.get("horizontal_scroll") is False, "fixed camera contract drift")
    require(float(camera.get("camera_displacement_px", -1.0)) == 0.0, "camera displacement must be zero")
    require(
        manifest.get("human_review_keys") == config.get("human_review_keys")
        and len(config["human_review_keys"]) == 9
        and "native_naturalness" in config["human_review_keys"],
        "nine-item human review contract drift",
    )

    source = REPO / config["source"]["panorama_file"]
    require(source.is_file() and sha256(source) == config["source"]["panorama_sha256"], "source drift")
    root = REPO / config["outputs"]["artifact_root"]
    require(root.is_dir(), "H2 v11 candidate root missing")
    outputs = manifest["outputs"]
    validate_video(outputs["scene_native"], root, (1920, 1080))
    validate_video(outputs["abstract_pacer"], root, (1920, 1080))
    validate_video(outputs["paired_review"], root, (3840, 1200))
    validate_fixed_camera_media_health(ffmpeg, root / outputs["scene_native"]["file"])
    validate_fixed_camera_media_health(ffmpeg, root / outputs["abstract_pacer"]["file"])

    audio_entry = outputs["ambient_audio"]
    audio_path = root / audio_entry["file"]
    require(audio_path.is_file(), "ambient WAV missing")
    require(audio_path.stat().st_size == audio_entry["size_bytes"], "ambient WAV size drift")
    require(sha256(audio_path) == audio_entry["sha256"], "ambient WAV hash drift")
    audio = stream(audio_entry["ffprobe"], "audio")
    require(audio.get("codec_name") == "pcm_s24le", "ambient WAV must be PCM 24-bit")
    require(audio.get("sample_rate") == "48000" and audio.get("channels") == 2, "ambient WAV format drift")
    loudness = manifest["audio_metrics"]
    require(-24.0 <= loudness["integrated_lufs_i"] <= -20.0, "ambient loudness out of range")
    require(loudness["true_peak_dbtp"] <= -3.0, "ambient true peak out of range")

    validate_sheet(outputs["review_keyframes"], "fade-H2-keyframes-v11.jpg")
    validate_sheet(outputs["grayscale_keyframes"], "fade-H2-grayscale-v11.jpg")
    render = manifest["render"]
    require(render["frame_count"] == 300 and render["fps"] == 30, "render timing drift")
    require(render.get("camera_mode") == "fixed", "render camera mode drift")
    require(render.get("horizontal_scroll") is False, "horizontal scroll must be disabled")
    require(float(render.get("camera_displacement_px", -1.0)) <= config["machine_gates"]["camera_displacement_px_max"], "camera moved")
    require(render.get("source_fit") == "cover_center_crop", "fixed background crop drift")
    require(
        render["max_raw_difference_outside_expected_mask"]
        == config["machine_gates"]["max_raw_difference_outside_expected_mask"],
        "conditions differ outside declared cue masks",
    )
    color = render["full_frame_color_metrics"]
    require(set(color) == {"0.00", "4.00", "9.50", "9.97"}, "full-frame color samples drift")
    require(color["0.00"]["color_u"] == 0.0, "first frame is not fully faded")
    require(color["9.50"]["color_u"] == 1.0 and color["9.97"]["color_u"] == 1.0, "native color endpoint drift")
    require(color["0.00"]["scene_mean_chroma"] <= 0.01, "scene first frame has a color flash")
    require(color["0.00"]["abstract_mean_chroma"] <= 0.01, "abstract first frame has a color flash")
    require(0.0 < color["4.00"]["scene_mean_chroma"] < color["9.50"]["scene_mean_chroma"], "scene color curve drift")
    require(
        0.0 < color["4.00"]["abstract_mean_chroma"] < color["9.50"]["abstract_mean_chroma"],
        "abstract color curve drift",
    )
    validate_geometry(render["cue_geometry_metrics"], config["machine_gates"])
    require(manifest["asset_status"]["formal_use_allowed"] is False, "H2 v11 cannot be formal-use enabled")
    require(bool(git_lines("check-ignore", "--", config["outputs"]["artifact_root"])), "H2 v11 media root must be ignored")
    require(not git_lines("ls-files", "--", config["outputs"]["artifact_root"]), "H2 v11 media must not be tracked")
    print(
        "PASS: V-04 H2 candidate-v11 machine gate; fixed camera, media, color envelope, water clipping, "
        "three-step geometry, actual-step fidelity, grayscale cues and condition parity verified; "
        "nine-item team-director review pending"
    )


if __name__ == "__main__":
    main()
