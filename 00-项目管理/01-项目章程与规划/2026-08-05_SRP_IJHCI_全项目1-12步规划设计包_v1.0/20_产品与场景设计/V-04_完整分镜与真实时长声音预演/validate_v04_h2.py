from __future__ import annotations

import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H2样片配置_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H2候选清单_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return [line for line in result.stdout.splitlines() if line]


def stream(probe: dict[str, object], codec_type: str) -> dict[str, object]:
    matches = [item for item in probe["streams"] if item.get("codec_type") == codec_type]
    require(len(matches) == 1, f"expected one {codec_type} stream")
    return matches[0]


def validate_video(entry: dict[str, object], root: Path, size: tuple[int, int]) -> None:
    path = root / entry["file"]
    require(path.is_file(), f"video missing: {path.name}")
    require(path.stat().st_size == entry["size_bytes"], f"video size drift: {path.name}")
    require(sha256(path) == entry["sha256"], f"video hash drift: {path.name}")
    probe = entry["ffprobe"]
    require(probe["format"].get("filename") == entry["file"], f"unstable probe path: {path.name}")
    video = stream(probe, "video")
    audio = stream(probe, "audio")
    require(video.get("codec_name") == "h264", f"video codec drift: {path.name}")
    require((video.get("width"), video.get("height")) == size, f"video dimensions drift: {path.name}")
    require(Fraction(video.get("avg_frame_rate")) == Fraction(30, 1), f"frame rate drift: {path.name}")
    require(video.get("pix_fmt") == "yuv420p", f"pixel format drift: {path.name}")
    require(audio.get("codec_name") == "aac", f"audio codec drift: {path.name}")
    require(audio.get("sample_rate") == "48000", f"audio sample rate drift: {path.name}")
    require(audio.get("channels") == 2, f"audio channel drift: {path.name}")
    duration = float(probe["format"]["duration"])
    require(abs(duration - 10.0) <= 0.06, f"duration drift: {path.name}={duration}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    require(manifest.get("candidate_id") == config.get("candidate_id"), "H2 candidate id drift")
    require(manifest.get("gate_status") == "PENDING_HUMAN_CONFIRMATION", "H2 human gate status drift")
    require(manifest.get("config_sha256") == sha256(CONFIG_PATH), "H2 config hash drift")
    require(manifest.get("h1_selection_sha256") == sha256(H1_SELECTION), "H1 selection hash drift")
    require(any(item["candidate_id"] == "fade-B" for item in h1["selections"]), "fade-B selection missing")
    source = REPO / config["source"]["panorama_file"]
    require(source.is_file() and sha256(source) == config["source"]["panorama_sha256"], "source drift")
    root = REPO / config["outputs"]["artifact_root"]
    require(root.is_dir(), "H2 candidate root missing")
    outputs = manifest["outputs"]
    validate_video(outputs["scene_native"], root, (1920, 1080))
    validate_video(outputs["abstract_pacer"], root, (1920, 1080))
    validate_video(outputs["paired_review"], root, (3840, 1200))

    audio_entry = outputs["ambient_audio"]
    audio_path = root / audio_entry["file"]
    require(audio_path.is_file(), "ambient WAV missing")
    require(audio_path.stat().st_size == audio_entry["size_bytes"], "ambient WAV size drift")
    require(sha256(audio_path) == audio_entry["sha256"], "ambient WAV hash drift")
    audio = stream(audio_entry["ffprobe"], "audio")
    require(
        audio_entry["ffprobe"]["format"].get("filename") == audio_entry["file"],
        "unstable ambient probe path",
    )
    require(audio.get("codec_name") == "pcm_s24le", "ambient WAV must be PCM 24-bit")
    require(audio.get("sample_rate") == "48000" and audio.get("channels") == 2, "ambient WAV format drift")
    metrics = manifest["audio_metrics"]
    require(-24.0 <= metrics["integrated_lufs_i"] <= -20.0, "ambient loudness out of range")
    require(metrics["true_peak_dbtp"] <= -3.0, "ambient true peak out of range")

    keyframe_entry = outputs["review_keyframes"]
    keyframe_path = HERE / keyframe_entry["file"]
    require(keyframe_path.is_file() and sha256(keyframe_path) == keyframe_entry["sha256"], "keyframes drift")
    with Image.open(keyframe_path) as image:
        require(image.size == (1920, 1110) and image.mode == "RGB", "keyframe sheet format drift")
    render = manifest["render"]
    require(render["frame_count"] == 300 and render["fps"] == 30, "render timing drift")
    require(render["max_raw_difference_outside_expected_mask"] == 0, "conditions differ outside cue masks")
    require(manifest["asset_status"]["formal_use_allowed"] is False, "H2 candidate cannot be formal-use enabled")
    ignored = git_lines("check-ignore", "--", config["outputs"]["artifact_root"])
    require(bool(ignored), "H2 artifact root must remain Git ignored")
    tracked = git_lines("ls-files", "--", config["outputs"]["artifact_root"])
    require(not tracked, "H2 media must not be Git tracked")
    print(
        f"PASS: V-04 H2 {config['candidate_id']} verified; 3 videos/1 PCM24 ambient/1 keyframe sheet exact; "
        "condition differences cue-only; human confirmation pending"
    )


if __name__ == "__main__":
    main()
