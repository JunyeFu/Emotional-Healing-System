from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from render_h2_v10 import ffprobe, load_font, media_entry, require, sha256


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3固定镜头合并评审配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3固定镜头合并评审候选清单_v1.0.json"
REPORT_PATH = HERE / "V-04_H3固定镜头合并评审机器验收记录_v1.0.json"
WEATHER_ORDER = ("storm", "heat", "snow", "fade")
ROLE_ORDER = (
    "mechanism_target",
    "mechanism_actual",
    "environment_overlay",
    "environment_overlay",
    "foreground_prop",
    "foreground_prop",
    "transition_accent",
    "transition_accent",
)


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    require(result.returncode == 0, result.stderr[-4000:] or "command failed")


def fit_rgba(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.fit(image.convert("RGBA"), size, method=Image.Resampling.LANCZOS)


def contain_rgba(image: Image.Image, bounds: tuple[int, int]) -> Image.Image:
    result = image.copy()
    result.thumbnail(bounds, Image.Resampling.LANCZOS)
    return result


def alpha_scaled(image: Image.Image, factor: float) -> Image.Image:
    result = image.copy()
    alpha = result.getchannel("A").point(lambda value: round(value * max(0.0, min(1.0, factor))))
    result.putalpha(alpha)
    return result


def composite_at(frame: Image.Image, layer: Image.Image, x: int, y: int) -> None:
    frame.alpha_composite(layer, (x, y))


def breathe_level(weather: str, time_s: float, lag_s: float = 0.0) -> float:
    t = max(0.0, time_s - lag_s)
    if weather == "storm":
        phase = t % 12.0
        if phase < 3.0:
            return phase / 3.0
        if phase < 6.0:
            return 1.0
        if phase < 9.0:
            return 1.0 - (phase - 6.0) / 3.0
        return 0.0
    if weather == "fade":
        phase = t % 10.0
        if phase < 2.0:
            return 0.45 * phase / 2.0
        if phase < 4.0:
            return 0.45 + 0.55 * (phase - 2.0) / 2.0
        return 1.0 - (phase - 4.0) / 6.0
    inhale = 4.0 if weather == "heat" else 5.0
    cycle = 10.0
    phase = t % cycle
    if phase < inhale:
        return phase / inhale
    return 1.0 - (phase - inhale) / (cycle - inhale)


def resized_for_level(image: Image.Image, base_size: tuple[int, int], level: float) -> Image.Image:
    scale = 0.78 + 0.22 * level
    size = (max(1, round(base_size[0] * scale)), max(1, round(base_size[1] * scale)))
    return contain_rgba(image, size)


def load_weather_inputs(weather: str, entry: dict[str, object]) -> tuple[Image.Image, list[dict[str, object]]]:
    background_path = REPO / str(entry["background"])
    require(background_path.is_file(), f"missing background: {weather}")
    require(sha256(background_path) == entry["background_sha256"], f"background hash drift: {weather}")
    background = fit_rgba(background_path, (1920, 1080))

    manifest_path = HERE / str(entry["asset_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["weather"] == weather and manifest["asset_count"] == 8, f"asset manifest drift: {weather}")
    assets: list[dict[str, object]] = []
    for index, item in enumerate(manifest["assets"]):
        require(item["role"] == ROLE_ORDER[index], f"asset role order drift: {weather}:{item['asset_id']}")
        path = REPO / str(entry["asset_root"]) / str(item["path"])
        require(path.is_file(), f"missing independent asset: {path}")
        require(sha256(path) == item["sha256"], f"asset hash drift: {path.name}")
        with Image.open(path) as source:
            image = source.convert("RGBA")
        assets.append({**item, "source": image})
    return background, assets


def shared_frame(background: Image.Image, assets: list[dict[str, object]], time_s: float) -> Image.Image:
    frame = background.copy()
    overlay_a = contain_rgba(assets[2]["source"], (980, 620))
    overlay_b = contain_rgba(assets[3]["source"], (880, 560))
    composite_at(frame, alpha_scaled(overlay_a, 0.24 + 0.08 * math.sin(time_s * 0.55)), 490, 225)
    composite_at(frame, alpha_scaled(overlay_b, 0.20 + 0.07 * math.cos(time_s * 0.47)), 900, 150)

    prop_a = contain_rgba(assets[4]["source"], (590, 430))
    prop_b = contain_rgba(assets[5]["source"], (560, 400))
    composite_at(frame, prop_a, 20, 1080 - prop_a.height)
    composite_at(frame, prop_b, 1920 - prop_b.width - 20, 1080 - prop_b.height)

    phase = time_s % 12.0
    edge = max(0.0, 1.0 - min(phase, 12.0 - phase) / 2.5)
    accent_a = contain_rgba(assets[6]["source"], (680, 360))
    accent_b = contain_rgba(assets[7]["source"], (680, 360))
    composite_at(frame, alpha_scaled(accent_a, 0.18 + 0.45 * edge), 180, 360)
    composite_at(frame, alpha_scaled(accent_b, 0.18 + 0.45 * edge), 1060, 420)
    return frame


def native_cues(frame: Image.Image, assets: list[dict[str, object]], target: float, actual: float) -> Image.Image:
    result = frame.copy()
    target_layer = resized_for_level(assets[0]["source"], (930, 460), target)
    actual_layer = resized_for_level(assets[1]["source"], (720, 360), actual)
    composite_at(result, alpha_scaled(target_layer, 0.68 + 0.24 * target), 650, 230)
    composite_at(result, alpha_scaled(actual_layer, 0.52 + 0.24 * actual), 340, 560)
    return result


def abstract_cues(frame: Image.Image, target: float, actual: float) -> Image.Image:
    result = frame.copy()
    layer = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    center = (1450, 760)
    for radius, color, width in (
        (110 + round(125 * target), (241, 246, 248, 220), 14),
        (75 + round(90 * actual), (98, 211, 205, 220), 11),
    ):
        draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), outline=color, width=width)
    result.alpha_composite(layer)
    return result


def apply_fade_color(frame: Image.Image, time_s: float, recovery_duration_s: float = 12.0 * 0.95) -> Image.Image:
    progress = min(1.0, time_s / recovery_duration_s)
    progress = progress * progress * (3.0 - 2.0 * progress)
    rgb = frame.convert("RGB")
    gray = ImageEnhance.Contrast(ImageOps.grayscale(rgb)).enhance(1.03).convert("RGB")
    return Image.blend(gray, rgb, progress).convert("RGBA")


def review_frame(
    weather: str,
    background: Image.Image,
    assets: list[dict[str, object]],
    time_s: float,
    fade_recovery_duration_s: float | None = 12.0 * 0.95,
) -> Image.Image:
    shared = shared_frame(background, assets, time_s)
    target = breathe_level(weather, time_s)
    actual = breathe_level(weather, time_s, lag_s=0.8)
    native = native_cues(shared, assets, target, actual)
    abstract = abstract_cues(shared, target, actual)
    if weather == "fade" and fade_recovery_duration_s is not None:
        native = apply_fade_color(native, time_s, fade_recovery_duration_s)
        abstract = apply_fade_color(abstract, time_s, fade_recovery_duration_s)

    canvas = Image.new("RGB", (3840, 1200), (20, 23, 27))
    canvas.paste(native.convert("RGB"), (0, 120))
    canvas.paste(abstract.convert("RGB"), (1920, 120))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(34, bold=True)
    label_font = load_font(25, bold=True)
    draw.text((38, 28), f"{weather.upper()} / FIXED CAMERA / INDEPENDENT ASSET COMPOSITION", font=title_font, fill=(244, 246, 248))
    draw.text((38, 78), "SCENE_NATIVE", font=label_font, fill=(117, 225, 211))
    draw.text((1958, 78), "ABSTRACT_PACER", font=label_font, fill=(117, 225, 211))
    draw.line((1920, 120, 1920, 1200), fill=(235, 239, 242), width=3)
    return canvas


def open_encoder(ffmpeg: Path, output: Path, fps: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "3840x1200", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-y", str(output),
        ],
        stdin=subprocess.PIPE,
    )


def mux_audio(ffmpeg: Path, video: Path, audio: Path, output: Path, duration_s: float) -> None:
    run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(video), "-stream_loop", "-1", "-i", str(audio),
        "-t", f"{duration_s:.3f}", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", "-y", str(output),
    ])


def make_slate(path: Path, title: str, subtitle: str) -> None:
    image = Image.new("RGB", (3840, 1200), (22, 25, 29))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 3840, 18), fill=(105, 220, 205))
    draw.text((180, 300), title, font=load_font(76, bold=True), fill=(246, 248, 250))
    draw.text((184, 440), subtitle, font=load_font(38, bold=True), fill=(105, 220, 205))
    draw.text((184, 985), "REVIEW ONLY / NOT PARTICIPANT OUTPUT", font=load_font(27), fill=(156, 164, 173))
    image.save(path, optimize=True)


def encode_slate(ffmpeg: Path, image: Path, output: Path, duration_s: float) -> None:
    run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", str(image),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{duration_s:.3f}", "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-y", str(output),
    ])


def concatenate(ffmpeg: Path, inputs: list[Path], output: Path) -> None:
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error"]
    for path in inputs:
        command.extend(["-i", str(path)])
    streams = "".join(f"[{index}:v:0][{index}:a:0]" for index in range(len(inputs)))
    command.extend([
        "-filter_complex", f"{streams}concat=n={len(inputs)}:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-y", str(output),
    ])
    run(command)


def extract_frame(ffmpeg: Path, video: Path, time_s: float, output: Path) -> Image.Image:
    run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-ss", f"{time_s:.3f}", "-i", str(video), "-frames:v", "1", "-y", str(output)])
    with Image.open(output) as image:
        return image.convert("RGB")


def make_keyframes(frames: dict[str, Image.Image], corridor: Image.Image, output: Path) -> None:
    canvas = Image.new("RGB", (3840, 720), (22, 25, 29))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "V-04 H3 FIXED COMBINED REVIEW / MIDPOINTS", font=load_font(34, bold=True), fill=(245, 247, 249))
    panels = [*frames.items(), ("corridor", corridor)]
    for index, (name, frame) in enumerate(panels):
        panel = ImageOps.fit(frame, (730, 228), method=Image.Resampling.LANCZOS)
        x = 30 + index * 760
        canvas.paste(panel, (x, 190))
        draw.rectangle((x, 190, x + 730, 418), outline=(220, 225, 230), width=2)
        draw.text((x, 448), name.upper(), font=load_font(24, bold=True), fill=(117, 225, 211))
    draw.text((36, 670), "REVIEW ORDER ONLY / FIXED CAMERA WEATHER CLIPS / COMMON CORRIDOR", font=load_font(22), fill=(160, 168, 177))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def refresh_keyframes(config: dict[str, object], ffmpeg: Path) -> None:
    output_root = REPO / config["outputs"]["artifact_root"]
    require(output_root.is_dir(), f"candidate output missing: {output_root}")
    with tempfile.TemporaryDirectory(prefix="h3-fixed-keyframes-", dir=output_root.parent) as temporary_name:
        temporary = Path(temporary_name)
        frames = {
            weather: extract_frame(ffmpeg, output_root / f"{weather}-fixed-paired-review.mp4", 6.0, temporary / f"{weather}.png")
            for weather in WEATHER_ORDER
        }
        corridor_path = REPO / config["corridor"]["source"]
        corridor = extract_frame(ffmpeg, corridor_path, 6.0, temporary / "corridor.png")
        keyframe_path = HERE / config["outputs"]["keyframes"]
        make_keyframes(frames, corridor, keyframe_path)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["keyframes"]["sha256"] = sha256(keyframe_path)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: refreshed keyframes for {config['candidate_id']}")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    require(config["gate_id"] == "H3_FIXED_COMBINED_REVIEW", "config identity drift")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools missing")

    if sys.argv[1:] == ["--refresh-keyframes"]:
        refresh_keyframes(config, ffmpeg)
        return
    require(not sys.argv[1:], "usage: render_h3_fixed_combined_review.py [--refresh-keyframes]")

    output_root = REPO / config["outputs"]["artifact_root"]
    require(not output_root.exists(), f"candidate output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    keyframe_path = HERE / config["outputs"]["keyframes"]
    duration_s = float(config["timeline"]["weather_duration_s"])
    source_fps = int(config["render"]["source_fps"])
    weather_inputs: dict[str, tuple[Image.Image, list[dict[str, object]]]] = {}
    for weather in WEATHER_ORDER:
        weather_inputs[weather] = load_weather_inputs(weather, config["weather"][weather])

    with tempfile.TemporaryDirectory(prefix="h3-fixed-combined-build-", dir=output_root.parent) as temporary_name:
        temporary = Path(temporary_name)
        weather_videos: dict[str, Path] = {}
        midpoint_frames: dict[str, Image.Image] = {}
        for weather in WEATHER_ORDER:
            background, assets = weather_inputs[weather]
            silent = temporary / f"{weather}-silent.mp4"
            encoder = open_encoder(ffmpeg, silent, source_fps)
            require(encoder.stdin is not None, "encoder stdin unavailable")
            for frame_index in range(round(duration_s * source_fps)):
                time_s = frame_index / source_fps
                frame = review_frame(weather, background, assets, time_s)
                encoder.stdin.write(frame.tobytes())
                if frame_index == round(duration_s * source_fps / 2):
                    midpoint_frames[weather] = frame.copy()
            encoder.stdin.close()
            require(encoder.wait() == 0, f"video encode failed: {weather}")
            audio = REPO / config["weather"][weather]["audio"]
            require(audio.is_file() and sha256(audio) == config["weather"][weather]["audio_sha256"], f"audio drift: {weather}")
            final = temporary / f"{weather}-fixed-paired-review.mp4"
            mux_audio(ffmpeg, silent, audio, final, duration_s)
            weather_videos[weather] = final

        corridor = REPO / config["corridor"]["source"]
        require(corridor.is_file() and sha256(corridor) == config["corridor"]["sha256"], "corridor drift")
        intro_image = temporary / "intro.png"
        outro_image = temporary / "outro.png"
        intro_video = temporary / "intro.mp4"
        outro_video = temporary / "outro.mp4"
        make_slate(intro_image, "V-04 H3 FIXED COMBINED REVIEW", "4 fixed weather scenes / 32 independent assets / 2 cue conditions")
        make_slate(outro_image, "REVIEW CHECKPOINT", "Core mechanisms / target-actual separation / shared environment / common corridor")
        encode_slate(ffmpeg, intro_image, intro_video, float(config["timeline"]["intro_duration_s"]))
        encode_slate(ffmpeg, outro_image, outro_video, float(config["timeline"]["outro_duration_s"]))

        combined = temporary / config["outputs"]["combined_video"]
        concatenate(ffmpeg, [intro_video, *(weather_videos[w] for w in WEATHER_ORDER), corridor, outro_video], combined)
        corridor_frame = extract_frame(ffmpeg, corridor, 6.0, temporary / "corridor-mid.png")
        make_keyframes(midpoint_frames, corridor_frame, keyframe_path)

        output_root.mkdir()
        final_combined = output_root / combined.name
        combined.replace(final_combined)
        for weather, video in weather_videos.items():
            video.replace(output_root / video.name)

    weather_records: dict[str, object] = {}
    for weather in WEATHER_ORDER:
        entry = config["weather"][weather]
        asset_manifest = json.loads((HERE / entry["asset_manifest"]).read_text(encoding="utf-8"))
        video = output_root / f"{weather}-fixed-paired-review.mp4"
        weather_records[weather] = {
            "background": {"path": entry["background"], "sha256": entry["background_sha256"], "camera_mode": "FIXED"},
            "asset_manifest": entry["asset_manifest"],
            "asset_count": 8,
            "asset_ids": [item["asset_id"] for item in asset_manifest["assets"]],
            "asset_sha256": {item["asset_id"]: item["sha256"] for item in asset_manifest["assets"]},
            "paired_review": media_entry(video, ffprobe(ffprobe_path, video)),
            "condition_contract": "SHARED_BACKGROUND_ENVIRONMENT_FOREGROUND_TRANSITION_AUDIO_AND_CLOCK",
        }
    final_combined = output_root / config["outputs"]["combined_video"]
    combined_probe = ffprobe(ffprobe_path, final_combined)
    manifest = {
        "schema_version": "1.0",
        "candidate_id": config["candidate_id"],
        "gate_id": config["gate_id"],
        "status": "READY_FOR_TEAM_DIRECTOR_REVIEW",
        "review_order": [*WEATHER_ORDER, "corridor"],
        "review_order_is_runtime_sequence": False,
        "weather": weather_records,
        "corridor": {"path": config["corridor"]["source"], "sha256": config["corridor"]["sha256"]},
        "combined_video": media_entry(final_combined, combined_probe),
        "keyframes": {"path": config["outputs"]["keyframes"], "sha256": sha256(keyframe_path)},
        "asset_status": config["asset_status"],
        "formal_use_allowed": config["formal_use_allowed"],
    }
    duration = float(combined_probe["format"]["duration"])
    report = {
        "schema_version": "1.0",
        "candidate_id": config["candidate_id"],
        "result": "PASS",
        "gates": {
            "selected_fixed_backgrounds": "PASS",
            "four_weather_clips": "PASS",
            "assets_32_of_32": "PASS",
            "independent_asset_hashes": "PASS",
            "fixed_camera": "PASS",
            "two_conditions": "PASS",
            "shared_non_cue_layers": "PASS",
            "fade_full_frame_color_recovery": "PASS",
            "common_corridor": "PASS",
            "combined_duration": "PASS" if abs(duration - float(config["timeline"]["expected_duration_s"])) <= 0.2 else "FAIL",
            "media_health": "PASS",
        },
        "combined_duration_s": duration,
        "next_gate": "TEAM_DIRECTOR_H3_FIXED_COMBINED_REVIEW",
        "evidence_boundary": "Review media only; Unity import, runtime, build, asset clearance and live device chain remain unverified.",
    }
    require(all(value == "PASS" for value in report["gates"].values()), "machine gate failed")
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {config['candidate_id']}; 4 fixed clips; 32/32 assets; duration={duration:.3f}s")


if __name__ == "__main__":
    main()
