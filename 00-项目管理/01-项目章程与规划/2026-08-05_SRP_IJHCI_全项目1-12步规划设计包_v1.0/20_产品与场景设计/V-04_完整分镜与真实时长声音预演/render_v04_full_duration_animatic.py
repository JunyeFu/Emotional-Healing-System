from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

import render_h3_fixed_combined_review as h3
from render_h2_v10 import ffprobe, load_font, media_entry, require, sha256


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_完整时长Animatic配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
WEATHER_ORDER = ("storm", "heat", "snow", "fade")


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    require(result.returncode == 0, result.stderr[-5000:] or "command failed")


def annotate(frame: Image.Image, text: str) -> Image.Image:
    result = frame.resize((1920, 600), Image.Resampling.LANCZOS).convert("RGB")
    draw = ImageDraw.Draw(result, "RGBA")
    draw.rounded_rectangle((1240, 9, 1908, 52), radius=5, fill=(8, 12, 16, 218), outline=(117, 225, 211, 230), width=2)
    draw.text((1260, 18), text, font=load_font(20, bold=True), fill=(245, 247, 249))
    return result


def open_encoder(ffmpeg: Path, output: Path, source_fps: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "1920x600", "-r", str(source_fps), "-i", "-", "-an", "-c:v", "libx264",
            "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-r", "30", "-y", str(output),
        ],
        stdin=subprocess.PIPE,
    )


def mux_audio(ffmpeg: Path, silent: Path, audio: Path | None, output: Path, duration_s: float) -> None:
    if audio is None:
        command = [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(silent), "-f", "lavfi", "-i",
            "anullsrc=r=48000:cl=stereo", "-t", f"{duration_s:.3f}", "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-shortest", "-y", str(output),
        ]
    else:
        command = [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(silent), "-stream_loop", "-1", "-i", str(audio),
            "-t", f"{duration_s:.3f}", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "128k", "-ar", "48000", "-ac", "2", "-shortest", "-y", str(output),
        ]
    run(command)


def render_active_exit(
    ffmpeg: Path,
    weather: str,
    background: Image.Image,
    assets: list[dict[str, object]],
    audio: Path,
    source_fps: int,
    output: Path,
) -> None:
    duration_s = 182.5
    silent = output.with_name(output.stem + "-silent.mp4")
    encoder = open_encoder(ffmpeg, silent, source_fps)
    require(encoder.stdin is not None, "encoder stdin unavailable")
    for frame_index in range(round(duration_s * source_fps)):
        module_time = frame_index / source_fps
        if module_time < 25.0:
            segment = "DEMO 0-25s"
        elif module_time < 175.0:
            segment = "CLOSED_LOOP 25-175s"
        else:
            segment = "LOCK_TRANSITION EXIT 175-182.5s"
        frame = h3.review_frame(
            weather,
            background,
            assets,
            module_time,
            fade_recovery_duration_s=175.0,
        )
        if module_time >= 175.0:
            shared = h3.shared_frame(background, assets, module_time)
            if weather == "fade":
                shared = h3.apply_fade_color(shared, 175.0, 175.0)
            neutral = Image.new("RGB", (3840, 1200), (20, 23, 27))
            neutral.paste(shared.convert("RGB"), (0, 120))
            neutral.paste(shared.convert("RGB"), (1920, 120))
            frame = Image.blend(frame.convert("RGB"), neutral, min(1.0, (module_time - 175.0) / 7.5))
        annotated = annotate(frame, f"{weather.upper()} | {segment}")
        encoder.stdin.write(annotated.tobytes())
    encoder.stdin.close()
    require(encoder.wait() == 0, f"active/exit encode failed: {weather}")
    mux_audio(ffmpeg, silent, audio, output, duration_s)


def render_baseline(
    ffmpeg: Path,
    weather: str | None,
    background: Image.Image | None,
    assets: list[dict[str, object]] | None,
    audio: Path | None,
    source_fps: int,
    output: Path,
) -> None:
    duration_s = 7.5
    silent = output.with_name(output.stem + "-silent.mp4")
    encoder = open_encoder(ffmpeg, silent, source_fps)
    require(encoder.stdin is not None, "encoder stdin unavailable")
    for frame_index in range(round(duration_s * source_fps)):
        local_time = frame_index / source_fps
        if weather is None:
            frame = Image.new("RGB", (3840, 1200), (18, 22, 26))
            draw = ImageDraw.Draw(frame)
            draw.text((1370, 460), "SESSION END", font=load_font(76, bold=True), fill=(245, 247, 249))
            label = "SESSION END 792.5-800s"
        else:
            require(background is not None and assets is not None, "baseline inputs missing")
            shared = h3.shared_frame(background, assets, local_time)
            if weather == "fade":
                shared = h3.apply_fade_color(shared, 0.0, 175.0)
            frame = Image.new("RGB", (3840, 1200), (20, 23, 27))
            frame.paste(shared.convert("RGB"), (0, 120))
            frame.paste(shared.convert("RGB"), (1920, 120))
            draw = ImageDraw.Draw(frame)
            draw.text((38, 28), f"{weather.upper()} / NEXT NEUTRAL BASELINE", font=load_font(34, bold=True), fill=(244, 246, 248))
            draw.text((38, 78), "SCENE_NATIVE", font=load_font(25, bold=True), fill=(117, 225, 211))
            draw.text((1958, 78), "ABSTRACT_PACER", font=load_font(25, bold=True), fill=(117, 225, 211))
            label = f"{weather.upper()} | LOCK_TRANSITION NEXT BASELINE"
        annotated = annotate(frame, label)
        encoder.stdin.write(annotated.tobytes())
    encoder.stdin.close()
    require(encoder.wait() == 0, "baseline encode failed")
    mux_audio(ffmpeg, silent, audio, output, duration_s)


def render_corridor(ffmpeg: Path, source: Path, output: Path, module_index: int) -> None:
    label_path = output.with_suffix(".png")
    label = Image.new("RGBA", (1920, 600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(label, "RGBA")
    draw.rounded_rectangle((1240, 9, 1908, 52), radius=5, fill=(8, 12, 16, 218), outline=(117, 225, 211, 230), width=2)
    draw.text((1260, 18), f"MODULE {module_index + 1} | NEUTRAL CORRIDOR", font=load_font(20, bold=True), fill=(245, 247, 249))
    label.save(label_path)
    run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-ss", "1.0", "-i", str(source), "-loop", "1", "-i", str(label_path),
        "-t", "10.0", "-filter_complex", "[0:v]scale=1920:600:flags=lanczos[v0];[v0][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "0:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-y", str(output),
    ])


def concatenate(ffmpeg: Path, inputs: list[Path], output: Path) -> None:
    listing = output.with_suffix(".txt")
    listing.write_text("".join(f"file '{path.as_posix()}'\n" for path in inputs), encoding="utf-8")
    run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", "-y", str(output)])


def extract_frame(ffmpeg: Path, video: Path, time_s: float, output: Path) -> Image.Image:
    run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-ss", f"{time_s:.3f}", "-i", str(video), "-frames:v", "1", "-y", str(output)])
    with Image.open(output) as image:
        return image.convert("RGB")


def make_keyframes(ffmpeg: Path, video: Path, output: Path) -> None:
    times = (0.5, 24.5, 100.0, 174.5, 187.5, 199.0)
    canvas = Image.new("RGB", (3840, 1160), (22, 25, 29))
    draw = ImageDraw.Draw(canvas)
    draw.text((30, 18), "V-04 FULL-DURATION ANIMATIC / 4 MODULES x 6 CHECKPOINTS", font=load_font(32, bold=True), fill=(245, 247, 249))
    with tempfile.TemporaryDirectory(prefix="v04-keyframes-") as temporary_name:
        temporary = Path(temporary_name)
        for row, weather in enumerate(WEATHER_ORDER):
            for column, relative_time in enumerate(times):
                absolute_time = row * 200.0 + relative_time
                frame = extract_frame(ffmpeg, video, absolute_time, temporary / f"{row}-{column}.png")
                panel = ImageOps.fit(frame, (610, 191), method=Image.Resampling.LANCZOS)
                x = 30 + column * 635
                y = 90 + row * 260
                canvas.paste(panel, (x, y))
                draw.rectangle((x, y, x + 610, y + 191), outline=(210, 216, 222), width=2)
                draw.text((x, y + 199), f"{weather.upper()}  t={absolute_time:.1f}s", font=load_font(18, bold=True), fill=(117, 225, 211))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    h3_config = json.loads((HERE / config["inputs"]["h3_config"]).read_text(encoding="utf-8"))
    h3_manifest = json.loads((HERE / config["inputs"]["h3_manifest"]).read_text(encoding="utf-8"))
    storyboard = json.loads((HERE / config["inputs"]["six_node_storyboard"]).read_text(encoding="utf-8"))
    require(config["review_order"] == list(WEATHER_ORDER), "review order drift")
    require(h3_config["candidate_id"] == h3_manifest["candidate_id"] == "h3-fixed-combined-review-candidate-v2", "H3 v2 input drift")
    require(storyboard["recommended_timeline"]["module_total_s"] == 200.0, "storyboard timeline drift")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools missing")
    output_root = REPO / config["outputs"]["artifact_root"]
    output_root.parent.mkdir(parents=True, exist_ok=True)
    source_fps = int(config["render"]["source_fps"])

    weather_inputs: dict[str, tuple[Image.Image, list[dict[str, object]]]] = {}
    audio_inputs: dict[str, Path] = {}
    for weather in WEATHER_ORDER:
        entry = h3_config["weather"][weather]
        weather_inputs[weather] = h3.load_weather_inputs(weather, entry)
        audio = REPO / entry["audio"]
        require(audio.is_file() and sha256(audio) == entry["audio_sha256"], f"audio drift: {weather}")
        audio_inputs[weather] = audio
    corridor = REPO / h3_config["corridor"]["source"]
    require(corridor.is_file() and sha256(corridor) == h3_config["corridor"]["sha256"], "corridor drift")

    timeline: list[dict[str, object]] = []
    cursor = 0.0
    for index, weather in enumerate(WEATHER_ORDER):
        for kind, duration in (
            ("demo_closed_loop_exit", 182.5),
            ("neutral_corridor", 10.0),
            ("next_neutral_baseline" if index + 1 < len(WEATHER_ORDER) else "session_end", 7.5),
        ):
            timeline.append({"module": weather, "kind": kind, "start_s": cursor, "end_s": cursor + duration})
            cursor += duration
    require(abs(cursor - 800.0) < 1e-9, f"timeline drift: {cursor}")

    final_audio = output_root / config["outputs"]["audio_video"]
    final_silent = output_root / config["outputs"]["silent_video"]
    existing_outputs = final_audio.is_file() and final_silent.is_file()
    require(existing_outputs or not output_root.exists(), f"incomplete candidate output exists: {output_root}")

    if not existing_outputs:
      with tempfile.TemporaryDirectory(prefix="v04-full-animatic-", dir=output_root.parent) as temporary_name:
        temporary = Path(temporary_name)
        segments: list[Path] = []
        for index, weather in enumerate(WEATHER_ORDER):
            background, assets = weather_inputs[weather]
            active_exit = temporary / f"{index:02d}-{weather}-active-exit.mp4"
            render_active_exit(ffmpeg, weather, background, assets, audio_inputs[weather], source_fps, active_exit)
            segments.append(active_exit)

            corridor_segment = temporary / f"{index:02d}-{weather}-corridor.mp4"
            render_corridor(ffmpeg, corridor, corridor_segment, index)
            segments.append(corridor_segment)

            baseline = temporary / f"{index:02d}-{weather}-baseline.mp4"
            if index + 1 < len(WEATHER_ORDER):
                next_weather = WEATHER_ORDER[index + 1]
                next_background, next_assets = weather_inputs[next_weather]
                render_baseline(ffmpeg, next_weather, next_background, next_assets, audio_inputs[next_weather], source_fps, baseline)
                baseline_kind = "next_neutral_baseline"
            else:
                render_baseline(ffmpeg, None, None, None, None, source_fps, baseline)
                baseline_kind = "session_end"
            segments.append(baseline)

        combined = temporary / config["outputs"]["audio_video"]
        concatenate(ffmpeg, segments, combined)
        silent = temporary / config["outputs"]["silent_video"]
        run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(combined), "-map", "0:v:0", "-c:v", "copy", "-an", "-movflags", "+faststart", "-y", str(silent)])
        output_root.mkdir()
        final_audio = output_root / combined.name
        final_silent = output_root / silent.name
        combined.replace(final_audio)
        silent.replace(final_silent)

    keyframes = HERE / config["outputs"]["keyframes"]
    make_keyframes(ffmpeg, final_audio, keyframes)
    audio_probe = ffprobe(ffprobe_path, final_audio)
    silent_probe = ffprobe(ffprobe_path, final_silent)
    node_timeline = []
    for index, weather in enumerate(WEATHER_ORDER):
        source_nodes = next(item["nodes"] for item in storyboard["weather_storyboards"] if item["technical_id"] == weather)
        for node in source_nodes:
            node_timeline.append({
                "module": weather,
                "node_id": node["node_id"],
                "module_time_s": node["module_time_s"],
                "session_time_s": index * 200.0 + node["module_time_s"],
                "purpose": node["purpose"],
                "visual_segment": node["visual_segment"],
                "authoritative_inputs": node["authoritative_inputs"],
                "audio_state": node["audio_state"],
                "fallback_state": node["fallback_state"],
            })
    manifest = {
        "schema_version": "1.0",
        "candidate_id": config["candidate_id"],
        "status": "MACHINE_CANDIDATE",
        "review_order": list(WEATHER_ORDER),
        "review_order_is_runtime_sequence": False,
        "timeline": timeline,
        "node_timeline": node_timeline,
        "audio_video": media_entry(final_audio, audio_probe),
        "silent_video": media_entry(final_silent, silent_probe),
        "keyframes": {"path": config["outputs"]["keyframes"], "sha256": sha256(keyframes)},
        "h3_candidate": h3_manifest["candidate_id"],
        "h3_manifest_sha256": sha256(HERE / config["inputs"]["h3_manifest"]),
        "storyboard_sha256": sha256(HERE / config["inputs"]["six_node_storyboard"]),
        "asset_status": config["asset_status"],
        "formal_use_allowed": config["formal_use_allowed"],
    }
    duration = float(audio_probe["format"]["duration"])
    report = {
        "schema_version": "1.0",
        "candidate_id": config["candidate_id"],
        "result": "PASS" if abs(duration - 800.0) <= 0.2 else "FAIL",
        "duration_s": duration,
        "modules": 4,
        "nodes": len(node_timeline),
        "has_audio_version": True,
        "has_silent_version": True,
        "next_gate": "V04_FULL_ANIMATIC_VALIDATION",
        "evidence_boundary": "Low-fidelity design review media only; Unity runtime, formal build, asset clearance and live device chain remain unverified.",
    }
    require(report["result"] == "PASS" and len(node_timeline) == 24, "full animatic machine gate failed")
    (HERE / config["outputs"]["manifest"]).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / config["outputs"]["machine_report"]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {config['candidate_id']}; duration={duration:.3f}s; nodes={len(node_timeline)}; audio+silent")


if __name__ == "__main__":
    main()
