from __future__ import annotations

import json
from pathlib import Path

from render_h2_v10 import ffprobe, require, sha256


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3固定镜头合并评审配置_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3固定镜头合并评审候选清单_v1.0.json"
REPORT_PATH = HERE / "V-04_H3固定镜头合并评审机器验收记录_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
WEATHER_ORDER = ("storm", "heat", "snow", "fade")
EXPECTED_ROLES = (
    "mechanism_target",
    "mechanism_actual",
    "environment_overlay",
    "environment_overlay",
    "foreground_prop",
    "foreground_prop",
    "transition_accent",
    "transition_accent",
)


def media_shape(probe: dict[str, object]) -> tuple[int, int, str, int, int]:
    streams = probe["streams"]
    video = next(stream for stream in streams if stream["codec_type"] == "video")
    audio = next(stream for stream in streams if stream["codec_type"] == "audio")
    return (
        int(video["width"]),
        int(video["height"]),
        video["r_frame_rate"],
        int(audio["sample_rate"]),
        int(audio["channels"]),
    )


def verify_media(ffprobe_path: Path, path: Path, expected_hash: str, duration_s: float, tolerance_s: float) -> None:
    require(path.is_file(), f"media missing: {path}")
    require(sha256(path) == expected_hash, f"media hash drift: {path}")
    probe = ffprobe(ffprobe_path, path)
    require(media_shape(probe) == (3840, 1200, "30/1", 48000, 2), f"media shape drift: {path}")
    duration = float(probe["format"]["duration"])
    require(abs(duration - duration_s) <= tolerance_s, f"media duration drift: {path}: {duration}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffprobe_path.is_file(), "locked ffprobe missing")

    require(config["candidate_id"] == manifest["candidate_id"] == report["candidate_id"], "candidate identity drift")
    require(config["gate_id"] == manifest["gate_id"] == "H3_FIXED_COMBINED_REVIEW", "gate identity drift")
    require(manifest["status"] == "READY_FOR_TEAM_DIRECTOR_REVIEW", "candidate status drift")
    require(manifest["review_order"] == [*WEATHER_ORDER, "corridor"], "review order drift")
    require(manifest["review_order_is_runtime_sequence"] is False, "review order promoted to runtime sequence")
    require(manifest["asset_status"] == "PENDING_G02_CLEARANCE", "asset clearance status drift")
    require(manifest["formal_use_allowed"] is False, "formal-use boundary drift")

    seen_assets: set[tuple[str, str]] = set()
    for weather in WEATHER_ORDER:
        source = config["weather"][weather]
        record = manifest["weather"][weather]
        background = REPO / source["background"]
        audio = REPO / source["audio"]
        require(background.is_file() and sha256(background) == source["background_sha256"], f"background drift: {weather}")
        require(audio.is_file() and sha256(audio) == source["audio_sha256"], f"audio drift: {weather}")
        require(record["background"]["camera_mode"] == "FIXED", f"camera mode drift: {weather}")
        require(record["background"]["sha256"] == source["background_sha256"], f"background record drift: {weather}")
        require(record["asset_count"] == 8, f"asset count drift: {weather}")
        require(record["condition_contract"] == "SHARED_BACKGROUND_ENVIRONMENT_FOREGROUND_TRANSITION_AUDIO_AND_CLOCK", f"condition contract drift: {weather}")

        asset_manifest_path = HERE / source["asset_manifest"]
        asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
        require(asset_manifest["weather"] == weather and asset_manifest["asset_count"] == 8, f"asset manifest drift: {weather}")
        require(tuple(item["role"] for item in asset_manifest["assets"]) == EXPECTED_ROLES, f"asset roles drift: {weather}")
        require(record["asset_ids"] == [item["asset_id"] for item in asset_manifest["assets"]], f"asset ids drift: {weather}")
        for item in asset_manifest["assets"]:
            asset_path = REPO / source["asset_root"] / item["path"]
            require(asset_path.is_file(), f"asset missing: {weather}/{item['asset_id']}")
            digest = sha256(asset_path)
            require(digest == item["sha256"] == record["asset_sha256"][item["asset_id"]], f"asset hash drift: {weather}/{item['asset_id']}")
            seen_assets.add((weather, item["asset_id"]))

        video_path = REPO / config["outputs"]["artifact_root"] / record["paired_review"]["file"]
        verify_media(ffprobe_path, video_path, record["paired_review"]["sha256"], 12.0, 0.1)

    require(len(seen_assets) == 32, f"expected 32 distinct weather assets, found {len(seen_assets)}")
    corridor = REPO / config["corridor"]["source"]
    require(corridor.is_file() and sha256(corridor) == config["corridor"]["sha256"] == manifest["corridor"]["sha256"], "corridor drift")

    combined = REPO / config["outputs"]["artifact_root"] / manifest["combined_video"]["file"]
    verify_media(ffprobe_path, combined, manifest["combined_video"]["sha256"], 68.0, 0.2)
    keyframes = HERE / manifest["keyframes"]["path"]
    require(keyframes.is_file() and sha256(keyframes) == manifest["keyframes"]["sha256"], "keyframe evidence drift")
    require(report["result"] == "PASS" and all(value == "PASS" for value in report["gates"].values()), "machine report is not PASS")
    require(report["next_gate"] == "TEAM_DIRECTOR_H3_FIXED_COMBINED_REVIEW", "next gate drift")
    print("PASS: H3 fixed combined review candidate; 4 clips; 32 assets; 68.0s; evidence boundary retained")


if __name__ == "__main__":
    main()
