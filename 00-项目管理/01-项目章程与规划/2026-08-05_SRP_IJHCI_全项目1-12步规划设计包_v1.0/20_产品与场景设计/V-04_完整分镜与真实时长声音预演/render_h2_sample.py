from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H2样片配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H2候选清单_v1.0.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def phase_state(t_s: float) -> tuple[str, float, float]:
    if t_s < 2.5:
        progress = smoothstep(t_s / 2.5)
        return "INHALE_1", progress, 0.18 + 0.68 * progress
    if t_s < 4.0:
        progress = smoothstep((t_s - 2.5) / 1.5)
        return "INHALE_2", progress, 0.86 + 0.14 * progress
    progress = smoothstep((t_s - 4.0) / 6.0)
    return "EXHALE_1", progress, 1.0 - 0.78 * progress


def interpolate_knots(t_s: float, knots: list[list[float]]) -> float:
    for (t0, v0), (t1, v1) in zip(knots, knots[1:], strict=False):
        if t_s <= t1:
            ratio = 0.0 if t1 == t0 else (t_s - t0) / (t1 - t0)
            return v0 + (v1 - v0) * smoothstep(ratio)
    return knots[-1][1]


def make_vertical_mask(height: int, width: int, start: int, end: int) -> Image.Image:
    values = np.zeros(height, dtype=np.uint8)
    values[end:] = 255
    if end > start:
        ramp = np.linspace(0.0, 1.0, end - start, endpoint=False)
        values[start:end] = np.round((ramp * ramp * (3.0 - 2.0 * ramp)) * 255).astype(np.uint8)
    return Image.fromarray(np.repeat(values[:, None], width, axis=1), mode="L")


def prepare_plate(source: Image.Image) -> Image.Image:
    resized = source.convert("RGB").resize((2304, 960), Image.Resampling.LANCZOS)
    blurred = source.convert("RGB").resize((2304, 1080), Image.Resampling.LANCZOS).filter(
        ImageFilter.GaussianBlur(18)
    )
    main = Image.new("RGB", (2304, 1080))
    main.paste(resized, (0, 60))
    alpha = np.zeros((1080, 2304), dtype=np.uint8)
    alpha[60:1020, :] = 255
    for row in range(30):
        value = round(255 * smoothstep(row / 30))
        alpha[60 + row, :] = value
        alpha[1019 - row, :] = value
    return Image.composite(main, blurred, Image.fromarray(alpha, mode="L"))


def shifted_crop(plate: Image.Image, offset: float) -> Image.Image:
    return plate.transform(
        (1920, 1080),
        Image.Transform.AFFINE,
        (1.0, 0.0, offset, 0.0, 1.0, 0.0),
        resample=Image.Resampling.BICUBIC,
    )


def make_fog_texture() -> Image.Image:
    rng = np.random.default_rng(40402)
    noise = rng.random((90, 192), dtype=np.float32)
    image = Image.fromarray(np.round(noise * 255).astype(np.uint8), mode="L")
    image = image.resize((2304, 1080), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(22))
    vertical = np.ones((1080, 2304), dtype=np.float32)
    vertical[:170, :] = np.linspace(0.15, 0.75, 170)[:, None]
    vertical[720:, :] = np.linspace(1.0, 0.1, 360)[:, None]
    values = np.asarray(image, dtype=np.float32) * vertical
    return Image.fromarray(np.clip(values, 0, 255).astype(np.uint8), mode="L")


def shared_environment(
    plate: Image.Image,
    fog_texture: Image.Image,
    masks: tuple[Image.Image, Image.Image, Image.Image],
    t_s: float,
    config: dict[str, object],
) -> Image.Image:
    speed_px_s = float(config["scroll"]["viewport_per_s"]) * 1920.0
    sky = shifted_crop(plate, 0.0)
    far = shifted_crop(plate, speed_px_s * float(config["scroll"]["far_ratio"]) * t_s)
    mid = shifted_crop(plate, speed_px_s * float(config["scroll"]["mid_ratio"]) * t_s)
    near = shifted_crop(plate, speed_px_s * float(config["scroll"]["near_ratio"]) * t_s)
    frame = Image.composite(far, sky, masks[0])
    frame = Image.composite(mid, frame, masks[1])
    frame = Image.composite(near, frame, masks[2])

    completeness = interpolate_knots(t_s, config["weather_preview"]["completeness_knots"])
    frame = ImageEnhance.Color(frame).enhance(0.72 + 0.45 * completeness)
    frame = ImageEnhance.Contrast(frame).enhance(0.90 + 0.20 * completeness)

    fog_offset = 18.0 * t_s
    fog_mask = shifted_crop(fog_texture.convert("RGB"), fog_offset).convert("L")
    fog_alpha = np.asarray(fog_mask, dtype=np.float32) * (0.035 + 0.012 * math.sin(0.37 * t_s + 0.4))
    fog_layer = Image.new("RGBA", frame.size, (208, 220, 223, 0))
    fog_layer.putalpha(Image.fromarray(np.clip(fog_alpha, 0, 35).astype(np.uint8), mode="L"))
    frame = Image.alpha_composite(frame.convert("RGBA"), fog_layer).convert("RGB")

    ripple = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ripple)
    for index in range(9):
        base_y = 690 + index * 31
        points = []
        for x in range(-40, 1961, 18):
            y = base_y + 3.2 * math.sin(x * 0.017 + t_s * (0.42 + index * 0.017) + index)
            points.append((x, y))
        draw.line(points, fill=(161, 183, 184, 18), width=2)
    return Image.alpha_composite(frame.convert("RGBA"), ripple).convert("RGB")


def phase_color(phase: str, alpha: int) -> tuple[int, int, int, int]:
    colors = {
        "INHALE_1": (92, 167, 163),
        "INHALE_2": (165, 115, 133),
        "EXHALE_1": (100, 137, 174),
    }
    red, green, blue = colors[phase]
    return red, green, blue, alpha


def clip_overlay(overlay: Image.Image, bounds: tuple[int, int, int, int]) -> Image.Image:
    clipped = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    clipped.paste(overlay.crop(bounds), (bounds[0], bounds[1]))
    return clipped


def scene_flow_layer(t_s: float, actual: bool) -> Image.Image:
    sample_t = max(0.0, t_s - 0.18) if actual else t_s
    phase, progress, value = phase_state(sample_t)
    if actual:
        value *= 0.86
        bounds = (350, 485, 900, 930)
        line_width = 5
        strands = 4
    else:
        bounds = (1005, 265, 1680, 760)
        line_width = 11
        strands = 6
    x0, y0, x1, y1 = bounds
    width = x1 - x0
    height = y1 - y0
    direction = -1.0 if phase == "EXHALE_1" else 1.0
    head = progress if direction > 0 else 1.0 - progress
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for strand in range(strands):
        phase_offset = strand * 0.55
        length = width * (0.28 + 0.48 * value)
        center = x0 + width * (0.15 + 0.70 * head)
        start = center - length / 2
        end = center + length / 2
        points = []
        for step in range(46):
            ratio = step / 45
            x = start + (end - start) * ratio
            wave = math.sin(ratio * math.tau * 1.35 + phase_offset + t_s * 0.18)
            y = y0 + height * (0.25 + 0.11 * strand) + wave * height * (0.018 + 0.010 * value)
            points.append((x, y))
        alpha = 95 if actual else 122
        draw.line(points, fill=phase_color(phase, alpha), width=line_width, joint="curve")
    glow = overlay.filter(ImageFilter.GaussianBlur(12 if actual else 18))
    combined = Image.alpha_composite(glow, overlay)
    return clip_overlay(combined, bounds)


def abstract_layer(t_s: float) -> Image.Image:
    target_phase, _, target_value = phase_state(t_s)
    actual_phase, _, actual_value = phase_state(max(0.0, t_s - 0.18))
    actual_value *= 0.86
    center_x, center_y = 960, 540
    outer_radius = 94 + 38 * target_value
    inner_radius = 62 + 29 * actual_value
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse(
        (center_x - outer_radius, center_y - outer_radius, center_x + outer_radius, center_y + outer_radius),
        outline=phase_color(target_phase, 210),
        width=8,
    )
    draw.ellipse(
        (center_x - inner_radius, center_y - inner_radius, center_x + inner_radius, center_y + inner_radius),
        outline=phase_color(actual_phase, 165),
        width=6,
    )
    glow = overlay.filter(ImageFilter.GaussianBlur(10))
    combined = Image.alpha_composite(glow, overlay)
    return clip_overlay(combined, (790, 370, 1130, 710))


def participant_frames(environment: Image.Image, t_s: float) -> tuple[Image.Image, Image.Image]:
    scene = Image.alpha_composite(environment.convert("RGBA"), scene_flow_layer(t_s, actual=False))
    scene = Image.alpha_composite(scene, scene_flow_layer(t_s, actual=True)).convert("RGB")
    abstract = Image.alpha_composite(environment.convert("RGBA"), abstract_layer(t_s)).convert("RGB")
    return scene, abstract


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(path, size) if path.is_file() else ImageFont.load_default(size=size)


def review_frame(scene: Image.Image, abstract: Image.Image, t_s: float) -> Image.Image:
    phase, _, _ = phase_state(t_s)
    canvas = Image.new("RGB", (3840, 1200), (20, 23, 27))
    canvas.paste(scene, (0, 120))
    canvas.paste(abstract, (1920, 120))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(24)
    draw.text((36, 18), "V-04 H2 / FADE-B / DESIGN_PREVIEW_ONLY", font=title_font, fill=(244, 244, 244))
    draw.text((36, 68), f"t={t_s:05.2f}s  phase={phase}  shared background/audio/trace", font=label_font, fill=(195, 202, 208))
    draw.text((1380, 68), "SCENE_NATIVE", font=label_font, fill=(158, 211, 202))
    draw.text((3300, 68), "ABSTRACT_PACER", font=label_font, fill=(190, 177, 220))
    return canvas


def open_video_encoder(ffmpeg: Path, output: Path, size: tuple[int, int], fps: int, log: Path) -> subprocess.Popen:
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s:v",
        f"{size[0]}x{size[1]}",
        "-r",
        str(fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-y",
        str(output),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log.open("wb"))


def moving_average(values: np.ndarray, width: int) -> np.ndarray:
    cumulative = np.cumsum(np.insert(values, 0, 0.0))
    filtered = (cumulative[width:] - cumulative[:-width]) / width
    left = width // 2
    right = len(values) - len(filtered) - left
    return np.pad(filtered, (left, right), mode="edge")


def write_pcm24(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    clipped = np.clip(samples, -0.999999, 0.999999)
    integers = np.round(clipped * 8388607.0).astype(np.int32).reshape(-1)
    unsigned = integers.astype(np.uint32) & 0xFFFFFF
    packed = np.empty((len(unsigned), 3), dtype=np.uint8)
    packed[:, 0] = unsigned & 0xFF
    packed[:, 1] = (unsigned >> 8) & 0xFF
    packed[:, 2] = (unsigned >> 16) & 0xFF
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(3)
        stream.setframerate(sample_rate)
        stream.writeframes(packed.tobytes())


def make_audio(path: Path, sample_rate: int, duration_s: float) -> None:
    rng = np.random.default_rng(250825)
    count = round(sample_rate * duration_s)
    time = np.arange(count, dtype=np.float64) / sample_rate
    left_noise = rng.normal(0.0, 1.0, count)
    right_noise = rng.normal(0.0, 1.0, count)
    left = 0.72 * moving_average(left_noise, 320) + 0.28 * moving_average(left_noise, 2400)
    right = 0.72 * moving_average(right_noise, 360) + 0.28 * moving_average(right_noise, 2100)
    slow = 0.18 * np.sin(math.tau * 0.071 * time + 0.3) + 0.11 * np.sin(math.tau * 0.113 * time + 1.7)
    stereo = np.column_stack((left + slow, right + 0.9 * slow))
    stereo /= max(1e-9, float(np.max(np.abs(stereo))))
    write_pcm24(path, stereo * 0.28, sample_rate)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        capture_output=capture,
        text=capture,
        encoding="utf-8" if capture else None,
        errors="replace" if capture else None,
    )


def normalize_audio(ffmpeg: Path, source: Path, target: Path) -> None:
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-af",
            "loudnorm=I=-22:TP=-3.5:LRA=7",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-y",
            str(target),
        ]
    )


def mux(ffmpeg: Path, video: Path, audio: Path, output: Path) -> None:
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            "-y",
            str(output),
        ]
    )


def ffprobe(ffprobe_path: Path, path: Path) -> dict[str, object]:
    result = run(
        [
            str(ffprobe_path),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    )
    probe = json.loads(result.stdout)
    probe["format"]["filename"] = path.name
    return probe


def audio_metrics(ffmpeg: Path, path: Path) -> dict[str, float]:
    result = run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-22:TP=-3:LRA=7:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture=True,
    )
    combined = result.stdout + "\n" + result.stderr
    blocks = re.findall(r"\{\s*\"input_i\".*?\}", combined, flags=re.DOTALL)
    require(bool(blocks), "FFmpeg loudness report missing")
    data = json.loads(blocks[-1])
    return {"integrated_lufs_i": float(data["input_i"]), "true_peak_dbtp": float(data["input_tp"])}


def media_entry(path: Path, probe: dict[str, object]) -> dict[str, object]:
    return {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "ffprobe": probe,
    }


def make_keyframe_sheet(frames: list[tuple[float, Image.Image]], output: Path) -> None:
    canvas = Image.new("RGB", (1920, 1110), (22, 25, 29))
    font = load_font(24, bold=True)
    small = load_font(20)
    draw = ImageDraw.Draw(canvas)
    for row, (t_s, review) in enumerate(frames):
        thumbnail = review.crop((0, 120, 3840, 1200)).resize((1920, 540), Image.Resampling.LANCZOS)
        thumbnail = thumbnail.resize((960, 270), Image.Resampling.LANCZOS)
        y = 90 + row * 340
        canvas.paste(thumbnail, (480, y))
        phase, _, _ = phase_state(t_s)
        draw.text((40, y), f"t={t_s:.2f}s", font=font, fill=(242, 242, 242))
        draw.text((40, y + 42), phase, font=small, fill=(183, 199, 205))
        draw.rectangle((480, y, 1439, y + 269), outline=(225, 225, 225), width=2)
    draw.text((40, 22), "V-04 H2 / FADE-B / KEYFRAME REVIEW", font=font, fill=(245, 245, 245))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    require(config["gate_id"] == "H2", "config gate drift")
    require(any(item["candidate_id"] == "fade-B" for item in h1["selections"]), "fade-B is not H1 selected")
    source = REPO / config["source"]["panorama_file"]
    require(source.is_file(), f"panorama missing: {source}")
    require(sha256(source) == config["source"]["panorama_sha256"], "panorama hash mismatch")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools are missing")

    output_root = REPO / config["outputs"]["artifact_root"]
    require(not output_root.exists(), f"candidate output already exists: {output_root}")
    build_parent = output_root.parent
    build_parent.mkdir(parents=True, exist_ok=True)
    fps = int(config["timeline"]["fps"])
    frame_count = int(config["timeline"]["frame_count"])
    duration_s = float(config["timeline"]["duration_s"])
    keyframes: list[tuple[float, Image.Image]] = []
    max_outside_difference = 0

    with tempfile.TemporaryDirectory(prefix=f"{config['candidate_id']}-build-", dir=build_parent) as temporary:
        build = Path(temporary)
        with Image.open(source) as image:
            plate = prepare_plate(image)
        fog = make_fog_texture()
        masks = (
            make_vertical_mask(1080, 1920, 190, 520),
            make_vertical_mask(1080, 1920, 410, 760),
            make_vertical_mask(1080, 1920, 650, 930),
        )
        silent_scene = build / "scene-silent.mp4"
        silent_abstract = build / "abstract-silent.mp4"
        silent_review = build / "review-silent.mp4"
        logs = [build / "scene-encode.log", build / "abstract-encode.log", build / "review-encode.log"]
        encoders = (
            open_video_encoder(ffmpeg, silent_scene, (1920, 1080), fps, logs[0]),
            open_video_encoder(ffmpeg, silent_abstract, (1920, 1080), fps, logs[1]),
            open_video_encoder(ffmpeg, silent_review, (3840, 1200), fps, logs[2]),
        )
        diff_mask = np.zeros((1080, 1920), dtype=bool)
        diff_mask[245:950, 320:930] = True
        diff_mask[245:785, 975:1710] = True
        diff_mask[340:740, 760:1160] = True
        try:
            for frame_index in range(frame_count):
                t_s = frame_index / fps
                environment = shared_environment(plate, fog, masks, t_s, config)
                scene, abstract = participant_frames(environment, t_s)
                review = review_frame(scene, abstract, t_s)
                scene_array = np.asarray(scene, dtype=np.int16)
                abstract_array = np.asarray(abstract, dtype=np.int16)
                outside = np.abs(scene_array - abstract_array)[~diff_mask]
                if outside.size:
                    max_outside_difference = max(max_outside_difference, int(outside.max()))
                encoders[0].stdin.write(scene.tobytes())
                encoders[1].stdin.write(abstract.tobytes())
                encoders[2].stdin.write(review.tobytes())
                if frame_index in {30, 105, 240}:
                    keyframes.append((t_s, review.copy()))
        finally:
            for encoder in encoders:
                if encoder.stdin:
                    encoder.stdin.close()
            for encoder in encoders:
                return_code = encoder.wait()
                require(return_code == 0, f"video encoder failed with exit code {return_code}")

        raw_audio = build / "ambient-raw.wav"
        normalized_audio = build / config["outputs"]["ambient_audio"]
        make_audio(raw_audio, int(config["audio"]["sample_rate_hz"]), duration_s)
        normalize_audio(ffmpeg, raw_audio, normalized_audio)
        final_scene = build / config["outputs"]["scene_native_video"]
        final_abstract = build / config["outputs"]["abstract_pacer_video"]
        final_review = build / config["outputs"]["paired_review_video"]
        mux(ffmpeg, silent_scene, normalized_audio, final_scene)
        mux(ffmpeg, silent_abstract, normalized_audio, final_abstract)
        mux(ffmpeg, silent_review, normalized_audio, final_review)
        for path in (raw_audio, silent_scene, silent_abstract, silent_review, *logs):
            path.unlink(missing_ok=True)

        review_keyframes = HERE / config["outputs"]["review_keyframes"]
        make_keyframe_sheet(keyframes, review_keyframes)
        probes = {
            "scene_native": ffprobe(ffprobe_path, final_scene),
            "abstract_pacer": ffprobe(ffprobe_path, final_abstract),
            "paired_review": ffprobe(ffprobe_path, final_review),
            "ambient_audio": ffprobe(ffprobe_path, normalized_audio),
        }
        metrics = audio_metrics(ffmpeg, normalized_audio)
        manifest = {
            "schema_version": "1.0",
            "task_id": "V-04",
            "gate_id": "H2",
            "candidate_id": config["candidate_id"],
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "h1_selection_sha256": sha256(H1_SELECTION),
            "source": {
                "file": config["source"]["panorama_file"],
                "sha256": sha256(source),
                "width": 1942,
                "height": 809,
            },
            "render": {
                "duration_s": duration_s,
                "fps": fps,
                "frame_count": frame_count,
                "max_raw_difference_outside_expected_mask": max_outside_difference,
                "difference_mask_policy": "cue layers only",
                "scroll_last_frame_near_offset_px": 1920.0 * 0.02 * ((frame_count - 1) / fps),
            },
            "audio_metrics": metrics,
            "outputs": {
                "scene_native": media_entry(final_scene, probes["scene_native"]),
                "abstract_pacer": media_entry(final_abstract, probes["abstract_pacer"]),
                "paired_review": media_entry(final_review, probes["paired_review"]),
                "ambient_audio": media_entry(normalized_audio, probes["ambient_audio"]),
                "review_keyframes": {
                    "file": review_keyframes.relative_to(HERE).as_posix(),
                    "size_bytes": review_keyframes.stat().st_size,
                    "sha256": sha256(review_keyframes),
                    "width": 1920,
                    "height": 1110,
                },
            },
            "asset_status": {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False},
            "gate_status": "PENDING_HUMAN_CONFIRMATION",
            "next_if_pass": "render fade default 200-second module",
            "evidence_boundary": "H2 candidate verifies local continuity, cue parity, preview speed and temporary sound identity only.",
        }
        output_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"PASS: rendered V-04 H2 {config['candidate_id']}; 300 shared frames; scene-native/abstract/paired review; "
        f"outside-mask diff={max_outside_difference}; H2 human confirmation pending"
    )


if __name__ == "__main__":
    main()
