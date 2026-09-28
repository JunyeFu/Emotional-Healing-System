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
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H2样片配置_v1.3.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
BACKGROUND_SELECTION = HERE / "V-04_H2背景选择记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H2候选清单_v1.3.json"


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
    source = source.convert("RGB")
    return ImageOps.fit(
        source,
        (1920, 1080),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


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
    t_s: float,
    config: dict[str, object],
) -> Image.Image:
    frame = plate.copy()
    frame = ImageEnhance.Contrast(frame).enhance(0.98)

    fog_offset = float(config["camera"]["max_fog_translation_px"]) * math.sin(0.19 * t_s + 0.4)
    fog_mask = shifted_crop(fog_texture.convert("RGB"), fog_offset).convert("L")
    fog_alpha = np.asarray(fog_mask, dtype=np.float32) * (0.035 + 0.012 * math.sin(0.37 * t_s + 0.4))
    fog_layer = Image.new("RGBA", frame.size, (208, 220, 223, 0))
    fog_layer.putalpha(Image.fromarray(np.clip(fog_alpha, 0, 35).astype(np.uint8), mode="L"))
    frame = Image.alpha_composite(frame.convert("RGBA"), fog_layer).convert("RGB")

    ripple = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ripple)
    ripple_amplitude = float(config["camera"]["ripple_amplitude_px"])
    for index in range(9):
        base_y = 690 + index * 31
        points = []
        for x in range(-40, 1961, 18):
            y = base_y + ripple_amplitude * math.sin(
                x * 0.017 + t_s * (0.37 + index * 0.019) + index * 1.13
            )
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


TARGET_MAIN_PATH = ((950.0, 580.0), (1120.0, 560.0), (1450.0, 665.0), (1840.0, 940.0))
TARGET_BRANCH_PATH = ((240.0, 690.0), (500.0, 675.0), (760.0, 625.0), (1040.0, 590.0))
ACTUAL_MAIN_PATH = ((470.0, 930.0), (690.0, 865.0), (940.0, 800.0), (1200.0, 750.0))
ACTUAL_BRANCH_PATH = ((350.0, 895.0), (550.0, 855.0), (750.0, 815.0), (930.0, 790.0))
ACTUAL_RETURN_PATH = ((1160.0, 760.0), (1360.0, 830.0), (1600.0, 930.0), (1860.0, 1040.0))


@lru_cache(maxsize=2)
def water_mask(role: str) -> Image.Image:
    mask = Image.new("L", (1920, 1080), 0)
    draw = ImageDraw.Draw(mask)
    if role == "target":
        polygon = [(650, 535), (1080, 500), (1570, 590), (1919, 735), (1919, 1079), (720, 1079), (480, 860)]
        draw.polygon(polygon, fill=255)
        draw.polygon([(0, 615), (530, 585), (1090, 545), (1160, 670), (600, 745), (0, 770)], fill=255)
    else:
        polygon = [(0, 775), (540, 710), (1240, 665), (1919, 750), (1919, 1079), (0, 1079)]
        draw.polygon(polygon, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(7))


def bezier_point(control: tuple[tuple[float, float], ...], u: float) -> tuple[float, float]:
    u = max(0.0, min(1.0, u))
    inverse = 1.0 - u
    x = (
        inverse**3 * control[0][0]
        + 3.0 * inverse * inverse * u * control[1][0]
        + 3.0 * inverse * u * u * control[2][0]
        + u**3 * control[3][0]
    )
    y = (
        inverse**3 * control[0][1]
        + 3.0 * inverse * inverse * u * control[1][1]
        + 3.0 * inverse * u * u * control[2][1]
        + u**3 * control[3][1]
    )
    return x, y


def ribbon_mask(
    control: tuple[tuple[float, float], ...],
    start_u: float,
    end_u: float,
    radius: float,
    alpha: float,
    t_s: float,
    seed: float,
) -> Image.Image:
    mask = Image.new("L", (1920, 1080), 0)
    if end_u <= start_u or alpha <= 0.0:
        return mask
    draw = ImageDraw.Draw(mask)
    steps = max(12, round(90 * (end_u - start_u)))
    for index in range(steps):
        ratio = index / max(1, steps - 1)
        u = start_u + (end_u - start_u) * ratio
        x, y = bezier_point(control, u)
        organic = 0.86 + 0.14 * math.sin(index * 1.73 + seed + t_s * 0.31)
        perspective = 0.68 + 0.52 * u
        local_radius = radius * organic * perspective
        local_alpha = round(alpha * (0.78 + 0.22 * math.sin(index * 1.19 + seed) ** 2))
        draw.ellipse(
            (x - local_radius * 1.65, y - local_radius, x + local_radius * 1.65, y + local_radius),
            fill=max(0, min(255, local_alpha)),
        )
    return mask.filter(ImageFilter.GaussianBlur(max(2.0, radius * 0.23)))


def reflection_patch_mask(
    control: tuple[tuple[float, float], ...],
    start_u: float,
    end_u: float,
    radius: float,
    alpha: float,
    t_s: float,
    seed: float,
    count: int,
) -> Image.Image:
    mask = Image.new("L", (1920, 1080), 0)
    if end_u <= start_u or alpha <= 0.0:
        return mask
    draw = ImageDraw.Draw(mask)
    for index in range(count):
        ratio = (index + 0.55) / count
        u = start_u + (end_u - start_u) * ratio
        x, y = bezier_point(control, u)
        x += 5.0 * math.sin(index * 1.9 + seed)
        y += 2.5 * math.sin(index * 1.3 + seed + t_s * 0.22)
        half_width = radius * (1.5 + 0.45 * math.sin(index * 1.7 + seed) ** 2)
        half_height = radius * (0.22 + 0.12 * math.sin(index * 1.1 + seed) ** 2)
        local_alpha = round(alpha * (0.62 + 0.30 * math.sin(index * 1.37 + seed) ** 2))
        draw.ellipse((x - half_width, y - half_height, x + half_width, y + half_height), fill=local_alpha)
    return mask.filter(ImageFilter.GaussianBlur(1.6))


def merge_masks(*masks: Image.Image) -> Image.Image:
    result = Image.new("L", (1920, 1080), 0)
    for mask in masks:
        result = ImageChops.lighter(result, mask)
    return result


def clip_to_water(layer: Image.Image, role: str) -> Image.Image:
    red, green, blue, alpha = layer.split()
    clipped_alpha = ImageChops.multiply(alpha, water_mask(role))
    return Image.merge("RGBA", (red, green, blue, clipped_alpha))


def water_color_layer(mask: Image.Image, role: str, blur_radius: float) -> Image.Image:
    body = Image.new("RGBA", (1920, 1080), cue_color(role, 0))
    body.putalpha(mask)
    glow = body.filter(ImageFilter.GaussianBlur(blur_radius))
    return clip_to_water(Image.alpha_composite(glow, body), role)


def reflection_marks(
    control: tuple[tuple[float, float], ...],
    start_u: float,
    end_u: float,
    role: str,
    t_s: float,
    alpha: int,
    count: int,
) -> Image.Image:
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for index in range(count):
        ratio = (index + 0.45) / count
        u = start_u + (end_u - start_u) * ratio
        x, y = bezier_point(control, u)
        width = 7.0 + 13.0 * u + 3.0 * math.sin(index * 1.7 + t_s * 0.4)
        rise = 1.5 + 1.5 * math.sin(index * 1.3 + t_s * 0.23)
        draw.arc(
            (x - width, y - 4.0 - rise, x + width, y + 4.0 + rise),
            start=8,
            end=172,
            fill=cue_color(role, max(0, alpha - (index % 3) * 12)),
            width=2 if role == "actual" else 3,
        )
    return clip_to_water(overlay, role)


def scene_target_tide_layer(t_s: float) -> Image.Image:
    phase, progress, _ = phase_state(t_s)
    if phase == "INHALE_1":
        main_end = 0.18 + 0.38 * progress
        mask = ribbon_mask(TARGET_MAIN_PATH, 0.03, main_end, 23.0 + 13.0 * progress, 74.0 + 42.0 * progress, t_s, 0.4)
        marks = reflection_marks(TARGET_MAIN_PATH, 0.05, main_end, "target", t_s, 108, 12)
    elif phase == "INHALE_2":
        main_end = 0.56
        retained = ribbon_mask(TARGET_MAIN_PATH, 0.03, main_end, 36.0, 116.0, t_s, 0.4)
        branch_end = 0.16 + 0.84 * progress
        supplement_core = ribbon_mask(
            TARGET_BRANCH_PATH,
            0.0,
            branch_end,
            6.0 + 3.0 * progress,
            42.0 + 20.0 * progress,
            t_s,
            2.1,
        )
        supplement_glints = reflection_patch_mask(
            TARGET_BRANCH_PATH,
            0.0,
            branch_end,
            10.0 + 4.0 * progress,
            72.0 + 18.0 * progress,
            t_s,
            2.1,
            9,
        )
        mask = merge_masks(retained, supplement_core, supplement_glints)
        marks = Image.alpha_composite(
            reflection_marks(TARGET_MAIN_PATH, 0.05, main_end, "target", t_s, 102, 12),
            reflection_marks(TARGET_BRANCH_PATH, 0.0, branch_end, "target", t_s, 68, 5),
        )
    else:
        head_u = 0.52 + 0.48 * progress
        tail_u = max(0.18, head_u - (0.34 + 0.22 * progress))
        exit_fade = 1.0 - smoothstep((progress - 0.78) / 0.22)
        main = ribbon_mask(
            TARGET_MAIN_PATH,
            tail_u,
            head_u,
            31.0 - 7.0 * progress,
            122.0 * exit_fade,
            t_s,
            0.4,
        )
        branch = ribbon_mask(
            TARGET_BRANCH_PATH,
            min(0.92, progress * 0.45),
            1.0,
            16.0,
            74.0 * max(0.0, 1.0 - 2.5 * progress) * exit_fade,
            t_s,
            2.1,
        )
        mask = merge_masks(main, branch)
        marks = reflection_marks(
            TARGET_MAIN_PATH,
            tail_u,
            head_u,
            "target",
            t_s,
            round(114 * exit_fade),
            15,
        )
    body = water_color_layer(ImageChops.multiply(mask, water_mask("target")), "target", 9.0)
    return clip_to_water(Image.alpha_composite(body, marks), "target")


def scene_actual_reflection_layer(
    t_s: float,
    lag_s: float,
    amplitude_ratio: float,
) -> tuple[Image.Image, str]:
    sample_t = max(0.0, t_s - lag_s)
    phase, progress, _ = phase_state(sample_t)
    opacity = amplitude_ratio
    if phase == "INHALE_1":
        end_u = 0.14 + 0.56 * progress
        mask = reflection_patch_mask(
            ACTUAL_MAIN_PATH, 0.04, end_u, 10.0 + 3.0 * progress, 76.0 * opacity, t_s, 3.2, 11
        )
        marks = reflection_marks(ACTUAL_MAIN_PATH, 0.04, end_u, "actual", t_s, round(92 * opacity), 7)
    elif phase == "INHALE_2":
        retained = reflection_patch_mask(ACTUAL_MAIN_PATH, 0.04, 0.70, 12.0, 76.0 * opacity, t_s, 3.2, 11)
        branch_end = 0.10 + 0.90 * progress
        supplement = reflection_patch_mask(
            ACTUAL_BRANCH_PATH,
            0.0,
            branch_end,
            8.0 + 2.0 * progress,
            70.0 * opacity,
            t_s,
            4.7,
            7,
        )
        mask = merge_masks(retained, supplement)
        marks = Image.alpha_composite(
            reflection_marks(ACTUAL_MAIN_PATH, 0.04, 0.70, "actual", t_s, round(90 * opacity), 7),
            reflection_marks(ACTUAL_BRANCH_PATH, 0.0, branch_end, "actual", t_s, round(82 * opacity), 5),
        )
    else:
        head_u = 0.12 + 0.88 * progress
        tail_u = max(0.0, head_u - 0.32)
        exit_fade = 1.0 - smoothstep((progress - 0.84) / 0.16)
        mask = reflection_patch_mask(
            ACTUAL_RETURN_PATH,
            tail_u,
            head_u,
            11.0,
            78.0 * opacity * exit_fade,
            t_s,
            5.3,
            10,
        )
        marks = reflection_marks(
            ACTUAL_RETURN_PATH,
            tail_u,
            head_u,
            "actual",
            t_s,
            round(92 * opacity * exit_fade),
            7,
        )
    body = water_color_layer(ImageChops.multiply(mask, water_mask("actual")), "actual", 3.0)
    return clip_to_water(Image.alpha_composite(body, marks), "actual"), phase


def abstract_layer(t_s: float, config: dict[str, object]) -> Image.Image:
    _, _, target_value = phase_state(t_s)
    lag_s = float(config["timeline"]["actual_lag_s"])
    amplitude_ratio = float(config["timeline"]["actual_amplitude_ratio"])
    _, _, actual_value = phase_state(max(0.0, t_s - lag_s))
    actual_value *= amplitude_ratio
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
    lag_s = float(config["timeline"]["actual_lag_s"])
    amplitude_ratio = float(config["timeline"]["actual_amplitude_ratio"])
    actual, _ = scene_actual_reflection_layer(t_s, lag_s, amplitude_ratio)
    scene = Image.alpha_composite(environment.convert("RGBA"), scene_target_tide_layer(t_s))
    scene = Image.alpha_composite(scene, actual).convert("RGB")
    abstract = Image.alpha_composite(environment.convert("RGBA"), abstract_layer(t_s, config)).convert("RGB")
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
    draw.text((36, 18), "V-04 H2 / FADE / CANDIDATE-V10", font=title_font, fill=(244, 244, 244))
    draw.text((36, 68), f"t={t_s:05.2f}s  phase={phase}  shared fixed camera/background/audio", font=label_font, fill=(195, 202, 208))
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


def cue_difference_mask() -> np.ndarray:
    mask = ImageChops.lighter(water_mask("target"), water_mask("actual"))
    rings = Image.new("L", (1920, 1080), 0)
    ImageDraw.Draw(rings).rectangle((790, 370, 1130, 710), fill=255)
    return np.asarray(ImageChops.lighter(mask, rings), dtype=np.uint8) > 0


def alpha_metrics(layer: Image.Image) -> tuple[np.ndarray, int, tuple[float, float]]:
    alpha = np.asarray(layer.getchannel("A"), dtype=np.uint8)
    active = alpha > 5
    area = int(active.sum())
    if area == 0:
        return alpha, 0, (0.0, 0.0)
    y, x = np.nonzero(active)
    return alpha, area, (float(x.mean()), float(y.mean()))


def grayscale_delta(layer: Image.Image) -> float:
    alpha = np.asarray(layer.getchannel("A"), dtype=np.uint8)
    active = alpha > 5
    if not active.any():
        return 0.0
    base = Image.new("RGB", (1920, 1080), (96, 96, 96))
    composite = Image.alpha_composite(base.convert("RGBA"), layer).convert("L")
    delta = np.abs(np.asarray(composite, dtype=np.int16) - 96)
    return float(delta[active].mean())


def cue_geometry_metrics(config: dict[str, object]) -> dict[str, object]:
    lag_s = float(config["timeline"]["actual_lag_s"])
    amplitude_ratio = float(config["timeline"]["actual_amplitude_ratio"])
    target_times = {"inhale_1": 2.47, "inhale_2": 3.97, "exhale": 7.0, "end": 9.97}
    targets = {name: scene_target_tide_layer(t_s) for name, t_s in target_times.items()}
    target_stats = {name: alpha_metrics(layer) for name, layer in targets.items()}
    inhale_1_alpha, inhale_1_area, inhale_1_center = target_stats["inhale_1"]
    inhale_2_alpha, inhale_2_area, _ = target_stats["inhale_2"]
    _, exhale_area, exhale_center = target_stats["exhale"]
    _, end_area, _ = target_stats["end"]
    inhale_1_active = inhale_1_alpha > 5
    inhale_2_active = inhale_2_alpha > 5
    retained = int((inhale_1_active & inhale_2_active).sum())
    added = int((~inhale_1_active & inhale_2_active).sum())
    start_head = bezier_point(TARGET_MAIN_PATH, 0.52)
    end_head = bezier_point(TARGET_MAIN_PATH, 1.0)
    head_travel = math.dist(start_head, end_head)
    target_water = np.asarray(water_mask("target"), dtype=np.uint8)
    actual_water = np.asarray(water_mask("actual"), dtype=np.uint8)
    target_outside = max(
        int(np.max(np.asarray(layer.getchannel("A"), dtype=np.uint8)[target_water == 0], initial=0))
        for layer in targets.values()
    )
    actual_samples = {
        "target_inhale_2_start": scene_actual_reflection_layer(2.50, lag_s, amplitude_ratio),
        "after_actual_lag": scene_actual_reflection_layer(2.75, lag_s, amplitude_ratio),
        "exhale": scene_actual_reflection_layer(7.0, lag_s, amplitude_ratio),
    }
    actual_outside = max(
        int(np.max(np.asarray(layer.getchannel("A"), dtype=np.uint8)[actual_water == 0], initial=0))
        for layer, _ in actual_samples.values()
    )
    return {
        "target_alpha_outside_water_max": target_outside,
        "actual_alpha_outside_water_max": actual_outside,
        "inhale_1_area_px": inhale_1_area,
        "inhale_2_area_px": inhale_2_area,
        "inhale_2_retained_ratio": round(retained / max(1, inhale_1_area), 6),
        "inhale_2_added_area_px": added,
        "inhale_2_area_ratio": round(inhale_2_area / max(1, inhale_1_area), 6),
        "exhale_area_px": exhale_area,
        "exhale_centroid_downstream_px": round(exhale_center[0] - inhale_1_center[0], 3),
        "exhale_centroid_down_px": round(exhale_center[1] - inhale_1_center[1], 3),
        "exhale_head_travel_px": round(head_travel, 3),
        "end_residual_area_ratio": round(end_area / max(1, exhale_area), 6),
        "grayscale_mean_delta": {
            name: round(grayscale_delta(targets[name]), 3) for name in ("inhale_1", "inhale_2", "exhale")
        },
        "actual_phase_at_target_inhale_2_start": actual_samples["target_inhale_2_start"][1],
        "actual_phase_after_lag": actual_samples["after_actual_lag"][1],
        "actual_exhale_phase": actual_samples["exhale"][1],
    }


def enforce_geometry_gates(metrics: dict[str, object], gates: dict[str, object]) -> None:
    require(
        metrics["target_alpha_outside_water_max"] <= gates["target_alpha_outside_water_max"],
        "target tide escaped the water mask",
    )
    require(
        metrics["actual_alpha_outside_water_max"] <= gates["actual_alpha_outside_water_max"],
        "actual reflection escaped the water mask",
    )
    require(metrics["inhale_1_area_px"] >= gates["inhale_1_min_area_px"], "first inhale tide is too small")
    require(
        metrics["inhale_2_retained_ratio"] >= gates["inhale_2_retained_ratio_min"],
        "supplemental inhale reset too much of the main tide",
    )
    require(
        metrics["inhale_2_added_area_px"] >= gates["inhale_2_added_area_px_min"],
        "supplemental inhale is not geometrically distinct",
    )
    require(
        metrics["inhale_2_area_ratio"] <= gates["inhale_2_area_ratio_max"],
        "supplemental inhale is not smaller than the main tide",
    )
    require(
        metrics["exhale_head_travel_px"] >= gates["exhale_head_travel_px_min"],
        "long exhale head travel is too short",
    )
    require(
        metrics["exhale_centroid_downstream_px"] >= gates["exhale_centroid_downstream_px_min"],
        "long exhale does not travel downstream",
    )
    require(
        metrics["end_residual_area_ratio"] <= gates["end_residual_area_ratio_max"],
        "target tide leaves a permanent end-state trace",
    )
    require(
        min(metrics["grayscale_mean_delta"].values()) >= gates["grayscale_mean_delta_min"],
        "target tide relies on color without enough grayscale contrast",
    )
    require(
        metrics["actual_phase_at_target_inhale_2_start"] == "INHALE_1",
        "actual trace inferred a supplemental inhale before the lagged actual step",
    )
    require(metrics["actual_phase_after_lag"] == "INHALE_2", "actual supplemental inhale did not appear after lag")
    require(metrics["actual_exhale_phase"] == "EXHALE_1", "actual long exhale step is not represented")


def make_keyframe_sheet(
    frames: list[tuple[float, Image.Image]],
    output: Path,
    *,
    grayscale: bool = False,
) -> None:
    canvas_height = 90 + len(frames) * 300
    canvas = Image.new("RGB", (1920, canvas_height), (22, 25, 29))
    font = load_font(24, bold=True)
    small = load_font(20)
    draw = ImageDraw.Draw(canvas)
    for row, (t_s, review) in enumerate(frames):
        thumbnail = review.crop((0, 120, 3840, 1200)).resize((1920, 540), Image.Resampling.LANCZOS)
        thumbnail = thumbnail.resize((960, 270), Image.Resampling.LANCZOS)
        if grayscale:
            thumbnail = thumbnail.convert("L").convert("RGB")
        y = 80 + row * 300
        canvas.paste(thumbnail, (480, y))
        phase, _, _ = phase_state(t_s)
        draw.text((40, y), f"t={t_s:.2f}s", font=font, fill=(242, 242, 242))
        draw.text((40, y + 42), phase, font=small, fill=(183, 199, 205))
        draw.rectangle((480, y, 1439, y + 269), outline=(225, 225, 225), width=2)
    title = "V-04 H2 / FADE V10 / GRAYSCALE GEOMETRY" if grayscale else "V-04 H2 / FADE V10 / KEYFRAME REVIEW"
    draw.text((40, 22), title, font=font, fill=(245, 245, 245))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    background_selection = json.loads(BACKGROUND_SELECTION.read_text(encoding="utf-8"))
    require(config["schema_version"] == "1.3", "config schema drift")
    require(config["gate_id"] == "H2" and config["candidate_id"] == "candidate-v10", "config identity drift")
    require(any(item["candidate_id"] == "fade-B" for item in h1["selections"]), "fade-B is not H1 selected")
    require(background_selection["candidate_id"] == config["source"]["selected_anchor_id"], "background selection drift")
    require(background_selection["decision"] == "PASS", "background has not passed human selection")
    require(config["camera"]["mode"] == "fixed" and config["camera"]["horizontal_scroll"] is False, "fixed camera drift")
    require(float(config["camera"]["camera_displacement_px"]) == 0.0, "camera displacement must be zero")
    design_contract = HERE / config["design_contract"]
    require(design_contract.is_file(), "candidate-v10 design contract missing")
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
    geometry_metrics = cue_geometry_metrics(config)
    enforce_geometry_gates(geometry_metrics, config["machine_gates"])
    keyframes: list[tuple[float, Image.Image]] = []
    full_frame_color_metrics: dict[str, dict[str, float]] = {}
    max_outside_difference = 0

    with tempfile.TemporaryDirectory(prefix=f"{config['candidate_id']}-build-", dir=build_parent) as temporary:
        build = Path(temporary)
        with Image.open(source) as image:
            source_size = image.size
            plate = prepare_plate(image)
        fog = make_fog_texture()
        silent_scene = build / "scene-silent.mp4"
        silent_abstract = build / "abstract-silent.mp4"
        silent_review = build / "review-silent.mp4"
        logs = [build / "scene-encode.log", build / "abstract-encode.log", build / "review-encode.log"]
        encoders = (
            open_video_encoder(ffmpeg, silent_scene, (1920, 1080), fps, logs[0]),
            open_video_encoder(ffmpeg, silent_abstract, (1920, 1080), fps, logs[1]),
            open_video_encoder(ffmpeg, silent_review, (3840, 1200), fps, logs[2]),
        )
        diff_mask = cue_difference_mask()
        try:
            for frame_index in range(frame_count):
                t_s = frame_index / fps
                environment = shared_environment(plate, fog, t_s, config)
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
                if frame_index in {0, 74, 119, 210, 285}:
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
        grayscale_keyframes = HERE / config["outputs"]["grayscale_keyframes"]
        make_keyframe_sheet(keyframes, grayscale_keyframes, grayscale=True)
        probes = {
            "scene_native": ffprobe(ffprobe_path, final_scene),
            "abstract_pacer": ffprobe(ffprobe_path, final_abstract),
            "paired_review": ffprobe(ffprobe_path, final_review),
            "ambient_audio": ffprobe(ffprobe_path, normalized_audio),
        }
        metrics = audio_metrics(ffmpeg, normalized_audio)
        manifest = {
            "schema_version": "1.3",
            "task_id": "V-04",
            "gate_id": "H2",
            "candidate_id": config["candidate_id"],
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "design_contract_sha256": sha256(design_contract),
            "h1_selection_sha256": sha256(H1_SELECTION),
            "background_selection_sha256": sha256(BACKGROUND_SELECTION),
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
                "difference_mask_policy": "water-clipped scene cues plus abstract ring bounds",
                "full_frame_color_metrics": full_frame_color_metrics,
                "cue_geometry_metrics": geometry_metrics,
                "native_color_reached_s": float(config["full_frame_color"]["native_color_reached_s"]),
                "camera_mode": "fixed",
                "camera_displacement_px": 0.0,
                "source_fit": "cover_center_crop",
                "horizontal_scroll": False,
                "max_fog_translation_px": float(config["camera"]["max_fog_translation_px"]),
                "ripple_amplitude_px": float(config["camera"]["ripple_amplitude_px"]),
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
                    "height": 1590,
                },
                "grayscale_keyframes": {
                    "file": grayscale_keyframes.relative_to(HERE).as_posix(),
                    "size_bytes": grayscale_keyframes.stat().st_size,
                    "sha256": sha256(grayscale_keyframes),
                    "width": 1920,
                    "height": 1590,
                },
            },
            "asset_status": {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False},
            "gate_status": "PENDING_HUMAN_CONFIRMATION",
            "human_review_keys": config["human_review_keys"],
            "next_if_pass": "record the nine-item team-director H2 review, then continue the remaining weather previews",
            "evidence_boundary": "H2 verifies the short preview only; Unity runtime, formal build and device chain remain unverified.",
        }
        output_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"PASS: rendered V-04 H2 {config['candidate_id']}; 300 shared fixed-camera frames; "
        f"full-frame color recovery; outside-mask diff={max_outside_difference}; H2 human confirmation pending"
    )


if __name__ == "__main__":
    main()
