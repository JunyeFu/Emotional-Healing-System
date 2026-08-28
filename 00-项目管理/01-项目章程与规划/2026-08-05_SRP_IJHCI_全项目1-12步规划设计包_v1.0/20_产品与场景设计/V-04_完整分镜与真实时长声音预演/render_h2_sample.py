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
CONFIG_PATH = HERE / "V-04_H2样片配置_v1.1.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H2候选清单_v1.1.json"


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

    frame = ImageEnhance.Contrast(frame).enhance(0.98)

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


def cue_color(role: str, alpha: int) -> tuple[int, int, int, int]:
    colors = {"target": (112, 191, 181), "actual": (235, 225, 196)}
    red, green, blue = colors[role]
    return red, green, blue, alpha


def clip_overlay(overlay: Image.Image, bounds: tuple[int, int, int, int]) -> Image.Image:
    clipped = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    clipped.paste(overlay.crop(bounds), (bounds[0], bounds[1]))
    return clipped


def smooth_array(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def elliptical_tide(
    width: int,
    height: int,
    center: tuple[float, float],
    radius: tuple[float, float],
    t_s: float,
) -> np.ndarray:
    y, x = np.mgrid[0:height, 0:width]
    normalized_x = x / max(1, width - 1)
    normalized_y = y / max(1, height - 1)
    wave = 0.025 * np.sin(normalized_x * math.tau * 2.2 + t_s * 0.45)
    dx = (normalized_x - center[0]) / radius[0]
    dy = (normalized_y + wave - center[1]) / radius[1]
    distance = np.sqrt(dx * dx + dy * dy)
    field = smooth_array((1.08 - distance) / 0.34)
    texture = 0.88 + 0.12 * np.sin(normalized_x * math.tau * 3.0 - normalized_y * 2.4 + t_s * 0.22)
    return np.clip(field * texture, 0.0, 1.0)


def scene_target_flow_layer(t_s: float) -> Image.Image:
    phase, progress, _ = phase_state(t_s)
    bounds = (1005, 265, 1680, 760)
    x0, y0, x1, y1 = bounds
    width = x1 - x0
    height = y1 - y0

    if phase == "INHALE_1":
        field = elliptical_tide(
            width,
            height,
            (0.50, 0.58 - 0.05 * progress),
            (0.40 + 0.14 * progress, 0.36 + 0.12 * progress),
            t_s,
        )
    elif phase == "INHALE_2":
        retained = elliptical_tide(width, height, (0.50, 0.53), (0.54, 0.48), t_s)
        supplement = elliptical_tide(
            width,
            height,
            (0.72 - 0.06 * progress, 0.70 - 0.10 * progress),
            (0.14 + 0.12 * progress, 0.12 + 0.10 * progress),
            t_s + 0.7,
        )
        field = np.maximum(retained, supplement)
    else:
        field = elliptical_tide(
            width,
            height,
            (0.50, 0.53 + 0.08 * progress),
            (0.54, 0.48),
            t_s,
        )

    mask_values = np.clip(field * 92.0, 0, 92).astype(np.uint8)
    mask = Image.fromarray(mask_values, mode="L").filter(ImageFilter.GaussianBlur(9))
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    flow = Image.new("RGBA", (width, height), cue_color("target", 0))
    flow.putalpha(mask)
    overlay.alpha_composite(flow, (x0, y0))
    draw = ImageDraw.Draw(overlay)
    direction = -1.0 if phase == "EXHALE_1" else 1.0
    for lane in range(4):
        points = []
        for step in range(40):
            ratio = step / 39
            x = x0 + width * (0.08 + 0.84 * ratio)
            y = y0 + height * (0.42 + 0.10 * lane) + 8 * math.sin(ratio * math.tau * 1.2 + t_s * direction)
            points.append((x, y))
        draw.line(points, fill=cue_color("target", 132), width=4)
    return clip_overlay(overlay, bounds)


def scene_actual_filament_layer(t_s: float) -> Image.Image:
    sample_t = max(0.0, t_s - 0.18)
    phase, progress, value = phase_state(sample_t)
    value *= 0.86
    bounds = (350, 485, 900, 930)
    line_width = 5
    strands = 4
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
        draw.line(points, fill=cue_color("actual", 150), width=line_width, joint="curve")
    glow = overlay.filter(ImageFilter.GaussianBlur(16))
    combined = Image.alpha_composite(glow, overlay)
    return clip_overlay(combined, bounds)


def abstract_layer(t_s: float) -> Image.Image:
    _, _, target_value = phase_state(t_s)
    _, _, actual_value = phase_state(max(0.0, t_s - 0.18))
    actual_value *= 0.86
    center_x, center_y = 960, 540
    outer_radius = 94 + 38 * target_value
    inner_radius = 62 + 29 * actual_value
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse(
        (center_x - outer_radius, center_y - outer_radius, center_x + outer_radius, center_y + outer_radius),
        outline=cue_color("target", 210),
        width=8,
    )
    draw.ellipse(
        (center_x - inner_radius, center_y - inner_radius, center_x + inner_radius, center_y + inner_radius),
        outline=cue_color("actual", 185),
        width=6,
    )
    glow = overlay.filter(ImageFilter.GaussianBlur(10))
    combined = Image.alpha_composite(glow, overlay)
    return clip_overlay(combined, (790, 370, 1130, 710))


def participant_frames(environment: Image.Image, t_s: float, config: dict[str, object]) -> tuple[Image.Image, Image.Image]:
    scene = Image.alpha_composite(environment.convert("RGBA"), scene_target_flow_layer(t_s))
    scene = Image.alpha_composite(scene, scene_actual_filament_layer(t_s)).convert("RGB")
    abstract = Image.alpha_composite(environment.convert("RGBA"), abstract_layer(t_s)).convert("RGB")
    native_reached_s = float(config["full_frame_color"]["native_color_reached_s"])
    color_u = smoothstep(t_s / native_reached_s)
    scene = ImageEnhance.Color(scene).enhance(color_u)
    abstract = ImageEnhance.Color(abstract).enhance(color_u)
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
    draw.text((36, 18), "V-04 H2 / FADE-B / CANDIDATE-V8", font=title_font, fill=(244, 244, 244))
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
    full_frame_color_metrics: dict[str, dict[str, float]] = {}
    max_outside_difference = 0

    with tempfile.TemporaryDirectory(prefix=f"{config['candidate_id']}-build-", dir=build_parent) as temporary:
        build = Path(temporary)
        with Image.open(source) as image:
            source_size = image.size
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
                scene, abstract = participant_frames(environment, t_s, config)
                review = review_frame(scene, abstract, t_s)
                scene_array = np.asarray(scene, dtype=np.int16)
                abstract_array = np.asarray(abstract, dtype=np.int16)
                outside = np.abs(scene_array - abstract_array)[~diff_mask]
                if outside.size:
                    max_outside_difference = max(max_outside_difference, int(outside.max()))
                encoders[0].stdin.write(scene.tobytes())
                encoders[1].stdin.write(abstract.tobytes())
                encoders[2].stdin.write(review.tobytes())
                if frame_index in {0, 120, 285, 299}:
                    scene_chroma = np.max(scene_array, axis=2) - np.min(scene_array, axis=2)
                    abstract_chroma = np.max(abstract_array, axis=2) - np.min(abstract_array, axis=2)
                    native_reached_s = float(config["full_frame_color"]["native_color_reached_s"])
                    full_frame_color_metrics[f"{t_s:.2f}"] = {
                        "color_u": round(smoothstep(t_s / native_reached_s), 6),
                        "scene_mean_chroma": round(float(np.mean(scene_chroma)), 3),
                        "abstract_mean_chroma": round(float(np.mean(abstract_chroma)), 3),
                    }
                if frame_index in {0, 120, 285}:
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
            "schema_version": "1.1",
            "task_id": "V-04",
            "gate_id": "H2",
            "candidate_id": config["candidate_id"],
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "h1_selection_sha256": sha256(H1_SELECTION),
            "source": {
                "file": config["source"]["panorama_file"],
                "sha256": sha256(source),
                "width": source_size[0],
                "height": source_size[1],
            },
            "render": {
                "duration_s": duration_s,
                "fps": fps,
                "frame_count": frame_count,
                "max_raw_difference_outside_expected_mask": max_outside_difference,
                "difference_mask_policy": "cue layers only",
                "full_frame_color_metrics": full_frame_color_metrics,
                "native_color_reached_s": float(config["full_frame_color"]["native_color_reached_s"]),
                "scroll_last_frame_near_offset_px": (
                    1920.0 * float(config["scroll"]["viewport_per_s"]) * ((frame_count - 1) / fps)
                ),
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
            "next_if_pass": "freeze H2 cue mapping and hand off the short-preview contract to Unity implementation",
            "evidence_boundary": "H2 verifies the short preview only; Unity runtime, formal build and device chain remain unverified.",
        }
        output_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"PASS: rendered V-04 H2 {config['candidate_id']}; 300 shared frames; full-frame color recovery; "
        f"outside-mask diff={max_outside_difference}; H2 human confirmation pending"
    )


if __name__ == "__main__":
    main()
