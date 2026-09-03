from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in HERE.parents if (parent / ".git").exists())
CONFIG = HERE / "V-04_完整时长Animatic配置_v1.0.json"
MANIFEST = HERE / "V-04_完整时长Animatic候选清单_v1.0.json"
REPORT = HERE / "V-04_完整时长Animatic深度机器验收记录_v1.0.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_at(ffmpeg: Path, video: Path, time_s: float, target: Path) -> np.ndarray:
    subprocess.run(
        [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-ss", str(time_s), "-i", str(video),
         "-frames:v", "1", "-y", str(target)],
        check=True,
    )
    return np.asarray(Image.open(target).convert("RGB"), dtype=np.float32)


def participant_parity(frame: np.ndarray) -> float:
    left = frame[95:585, :960]
    right = frame[95:585, 960:1920]
    keep = np.ones(left.shape[:2], dtype=bool)
    keep[45:455, 555:925] = False
    return float(np.abs(left - right)[keep].mean())


def saturation(frame: np.ndarray) -> float:
    rgb = frame[100:585, :900] / 255.0
    maximum = rgb.max(axis=2)
    minimum = rgb.min(axis=2)
    valid = maximum > 0.02
    values = np.zeros_like(maximum)
    values[valid] = (maximum[valid] - minimum[valid]) / maximum[valid]
    return float(values.mean())


def low_frequency_gray(frame: np.ndarray) -> np.ndarray:
    image = Image.fromarray(frame.astype(np.uint8)).crop((20, 100, 560, 570)).resize((135, 118))
    return np.asarray(image.convert("L"), dtype=np.float32)


def best_translation(first: np.ndarray, second: np.ndarray) -> tuple[int, int, float]:
    best = (99, 99, float("inf"))
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            y0, y1 = max(0, dy), min(first.shape[0], first.shape[0] + dy)
            x0, x1 = max(0, dx), min(first.shape[1], first.shape[1] + dx)
            other_y0, other_y1 = max(0, -dy), min(second.shape[0], second.shape[0] - dy)
            other_x0, other_x1 = max(0, -dx), min(second.shape[1], second.shape[1] - dx)
            score = float(np.abs(first[y0:y1, x0:x1] - second[other_y0:other_y1, other_x0:other_x1]).mean())
            if score < best[2]:
                best = (dx, dy, score)
    return best


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lock = json.loads((HERE / "V-04_toolchain-lock_v1.0.json").read_text(encoding="utf-8"))
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    artifact_root = REPO / config["outputs"]["artifact_root"]
    audio_video = artifact_root / config["outputs"]["audio_video"]
    silent_video = artifact_root / config["outputs"]["silent_video"]
    keyframes = HERE / config["outputs"]["keyframes"]

    require(manifest["candidate_id"] == "v04-full-duration-animatic-candidate-v1", "candidate drift")
    require(manifest["review_order"] == ["storm", "heat", "snow", "fade"], "review order drift")
    require(manifest["review_order_is_runtime_sequence"] is False, "review order mislabeled")
    require(manifest["formal_use_allowed"] is False, "candidate exceeds evidence boundary")
    require(manifest["asset_status"] == "TEMP_REFERENCE_ONLY_PENDING_G02_CLEARANCE", "asset status drift")
    require(len(manifest["timeline"]) == 12 and len(manifest["node_timeline"]) == 24, "timeline cardinality drift")
    require(manifest["timeline"][0]["start_s"] == 0.0 and manifest["timeline"][-1]["end_s"] == 800.0, "timeline bounds drift")
    require([entry["session_time_s"] for entry in manifest["node_timeline"]] ==
            [offset + value for offset in (0.0, 200.0, 400.0, 600.0) for value in (0.0, 25.0, 25.0, 100.0, 175.0, 200.0)],
            "six-node timing drift")
    for entry in manifest["node_timeline"]:
        require(entry["purpose"] and entry["authoritative_inputs"] and entry["audio_state"] and entry["fallback_state"],
                f"incomplete node contract: {entry['module']}/{entry['node_id']}")

    for path, key in ((audio_video, "audio_video"), (silent_video, "silent_video")):
        require(path.is_file(), f"missing media: {path}")
        require(sha256(path) == manifest[key]["sha256"], f"media hash drift: {path.name}")
        probe = manifest[key]["ffprobe"]
        require(abs(float(probe["format"]["duration"]) - 800.0) <= 0.05, f"duration drift: {path.name}")
        video_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
        audio_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
        require(len(video_streams) == 1 and video_streams[0]["width"] == 1920 and video_streams[0]["height"] == 600,
                f"video geometry drift: {path.name}")
        require(video_streams[0]["avg_frame_rate"] == "30/1", f"frame rate drift: {path.name}")
        if key == "audio_video":
            require(len(audio_streams) == 1 and audio_streams[0]["sample_rate"] == "48000" and audio_streams[0]["channels"] == 2,
                    "audio stream drift")
        else:
            require(not audio_streams, "silent candidate contains audio")
    require(keyframes.is_file() and sha256(keyframes) == manifest["keyframes"]["sha256"], "keyframe sheet drift")

    with tempfile.TemporaryDirectory(prefix="v04-deep-check-") as temp_name:
        temp = Path(temp_name)
        parity = {}
        camera = {}
        module_starts = {"storm": 0.0, "heat": 200.0, "snow": 400.0, "fade": 600.0}
        for weather, start in module_starts.items():
            first = frame_at(ffmpeg, audio_video, start + 50.0, temp / f"{weather}-50.png")
            second = frame_at(ffmpeg, audio_video, start + 100.0, temp / f"{weather}-100.png")
            parity[weather] = round(participant_parity(second), 4)
            camera[weather] = best_translation(low_frequency_gray(first), low_frequency_gray(second))
            require(parity[weather] <= 8.0, f"condition pixels diverged outside cue mask: {weather}={parity[weather]}")
            require(camera[weather][0:2] == (0, 0), f"camera translation detected: {weather}={camera[weather]}")

        fade_saturation = []
        for index, time_s in enumerate((600.5, 700.0, 774.5)):
            frame = frame_at(ffmpeg, audio_video, time_s, temp / f"fade-{index}.png")
            fade_saturation.append(saturation(frame))
        require(fade_saturation[0] + 0.08 < fade_saturation[1] < fade_saturation[2],
                f"fade recovery is not monotonic: {fade_saturation}")

        corridor_parity = {}
        for index, time_s in enumerate((187.5, 387.5, 587.5, 787.5)):
            frame = frame_at(ffmpeg, audio_video, time_s, temp / f"corridor-{index}.png")
            left = frame[100:585, :960]
            right = frame[100:585, 960:1920]
            corridor_parity[str(time_s)] = round(float(np.abs(left - right).mean()), 4)
            require(corridor_parity[str(time_s)] <= 3.0, f"corridor condition divergence: {time_s}")

    result = {
        "schema_version": "1.0",
        "candidate_id": manifest["candidate_id"],
        "status": "PASS",
        "checks": {
            "media_and_streams": "PASS",
            "timeline_and_24_nodes": "PASS",
            "condition_non_cue_pixel_parity": parity,
            "fixed_camera_translation_dx_dy_score": camera,
            "fade_mean_saturation": [round(value, 6) for value in fade_saturation],
            "corridor_condition_parity": corridor_parity,
        },
        "evidence_boundary": "DESIGN_AND_MEDIA_CANDIDATE_ONLY_NOT_UNITY_RUNTIME_NOT_FORMAL_BUILD_NOT_LIVE_DEVICE_CHAIN",
    }
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {manifest['candidate_id']}; 800s audio+silent; 24 nodes; pixel checks")


if __name__ == "__main__":
    main()
