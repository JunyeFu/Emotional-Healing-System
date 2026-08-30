from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from render_h2_v10 import (
    audio_metrics,
    ffprobe,
    load_font,
    media_entry,
    moving_average,
    mux,
    normalize_audio,
    open_video_encoder,
    require,
    sha256,
    smoothstep,
    write_pcm24,
)


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3_heat样片配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
H2_REVIEW = HERE / "V-04_H2人工评审记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3_heat候选清单_v1.0.json"
SIZE = (1920, 1080)


def phase_state(t_s: float) -> tuple[str, float]:
    if t_s < 4.0:
        return "INHALE", smoothstep(max(0.0, t_s) / 4.0)
    return "EXHALE", smoothstep(min(1.0, max(0.0, t_s - 4.0) / 6.0))


def actual_state(t_s: float, lag_s: float) -> tuple[str, float]:
    return phase_state(max(0.0, t_s - lag_s))


def prepare_scroll_plate(source: Image.Image, target_height: int) -> Image.Image:
    source = source.convert("RGB")
    target_width = round(source.width * target_height / source.height)
    require(target_width >= 2304, "heat source plate is too narrow for the frozen scroll")
    return source.resize((target_width, target_height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def salt_motes() -> tuple[tuple[float, float, float, float, int], ...]:
    rng = np.random.default_rng(30083017)
    motes = []
    for _ in range(145):
        motes.append(
            (
                float(rng.uniform(-120.0, 2040.0)),
                float(rng.uniform(420.0, 980.0)),
                float(rng.uniform(8.0, 31.0)),
                float(rng.uniform(11.0, 34.0)),
                int(rng.integers(10, 28)),
            )
        )
    return tuple(motes)


def apply_heat_haze(frame: Image.Image, t_s: float) -> Image.Image:
    array = np.asarray(frame, dtype=np.uint8).copy()
    top, bottom = 255, 815
    y = np.arange(top, bottom, dtype=np.float64)
    envelope = np.sin(np.pi * (y - top) / (bottom - top)) ** 1.35
    shifts = np.rint(
        envelope
        * (
            2.1 * np.sin(y * 0.071 + t_s * 0.31)
            + 1.4 * np.sin(y * 0.019 - t_s * 0.17 + 1.3)
        )
    ).astype(np.int32)
    x = np.arange(SIZE[0], dtype=np.int32)[None, :]
    source_x = np.clip(x - shifts[:, None], 0, SIZE[0] - 1)
    array[top:bottom] = array[top:bottom][np.arange(bottom - top)[:, None], source_x]
    return Image.fromarray(array, mode="RGB")


def draw_shared_dust(t_s: float) -> Image.Image:
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x0, y0, speed, lift, alpha in salt_motes():
        x = (x0 + speed * t_s) % 2160.0 - 120.0
        y = y0 - lift * math.sin(0.13 * t_s + x0 * 0.007)
        radius = 1.2 + 0.8 * math.sin(x0 * 0.021 + t_s * 0.09)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(215, 189, 143, alpha))
    return overlay.filter(ImageFilter.GaussianBlur(0.45))


def shared_environment(plate: Image.Image, t_s: float, config: dict[str, object]) -> tuple[Image.Image, float]:
    speed = float(config["camera"]["scroll_speed_viewport_per_s"])
    displacement = speed * SIZE[0] * t_s
    crop_y = int(config["camera"]["vertical_crop_y_px"])
    crop_x = min(plate.width - SIZE[0], int(round(displacement)))
    frame = plate.crop((crop_x, crop_y, crop_x + SIZE[0], crop_y + SIZE[1]))
    frame = ImageEnhance.Contrast(frame).enhance(1.035)
    frame = ImageEnhance.Color(frame).enhance(1.12)
    warm = Image.new("RGBA", SIZE, (249, 181, 104, 30))
    frame = Image.alpha_composite(frame.convert("RGBA"), warm).convert("RGB")
    frame = apply_heat_haze(frame, t_s)
    environment = Image.alpha_composite(frame.convert("RGBA"), draw_shared_dust(t_s)).convert("RGB")
    return environment, float(crop_x)


def quadratic_point(points: tuple[tuple[float, float], ...], u: float) -> tuple[float, float]:
    one = 1.0 - u
    return (
        one * one * points[0][0] + 2.0 * one * u * points[1][0] + u * u * points[2][0],
        one * one * points[0][1] + 2.0 * one * u * points[1][1] + u * u * points[2][1],
    )


def quadratic_length(points: tuple[tuple[float, float], ...]) -> float:
    samples = [quadratic_point(points, float(u)) for u in np.linspace(0.0, 1.0, 240)]
    return float(
        sum(math.hypot(right[0] - left[0], right[1] - left[1]) for left, right in zip(samples, samples[1:]))
    )


def clip_layer(layer: Image.Image, bounds: list[int], feather_px: int) -> Image.Image:
    left, top, right, bottom = (int(value) for value in bounds)
    clip_values = np.zeros((SIZE[1], SIZE[0]), dtype=np.float32)
    y, x = np.mgrid[top : bottom + 1, left : right + 1]
    distance = np.minimum.reduce((x - left, right - x, y - top, bottom - y)).astype(np.float32)
    u = np.clip(distance / feather_px, 0.0, 1.0)
    clip_values[top : bottom + 1, left : right + 1] = u * u * (3.0 - 2.0 * u)
    clip = Image.fromarray(np.round(clip_values * 255).astype(np.uint8), mode="L")
    clipped = layer.copy()
    clipped.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
    return clipped


def draw_wisp_segments(
    draw: ImageDraw.ImageDraw,
    path: tuple[tuple[float, float], ...],
    start_u: float,
    end_u: float,
    offset_x: float,
    offset_y: float,
    color: tuple[int, int, int, int],
    width: int,
    segment_shift: float,
) -> None:
    if end_u <= start_u:
        return
    windows = ((0.00, 0.27), (0.35, 0.60), (0.69, 0.96))
    for window_start, window_end in windows:
        segment_start = max(start_u, window_start + segment_shift)
        segment_end = min(end_u, window_end + segment_shift)
        if segment_end <= segment_start:
            continue
        values = np.linspace(segment_start, segment_end, 34)
        points = [quadratic_point(path, float(u)) for u in values]
        shifted = [(x + offset_x, y + offset_y) for x, y in points]
        draw.line(shifted, fill=color, width=width, joint="curve")


def draw_inhale_carrier(
    layer: Image.Image,
    progress: float,
    path: tuple[tuple[float, float], ...],
    spread_px: float,
    scale: float,
) -> None:
    draw = ImageDraw.Draw(layer)
    head = 0.08 + 0.92 * progress
    bands = (-1.0, -0.42, 0.12, 0.68, 1.0) if scale >= 0.9 else (-0.72, 0.0, 0.78)
    for index, band in enumerate(bands):
        shifted = (
            (path[0][0] + band * spread_px, path[0][1] + abs(band) * 15.0),
            (path[1][0] + band * spread_px * 0.48 + 13.0 * math.sin(index * 1.9), path[1][1] - 8.0 * math.cos(index)),
            (path[2][0] + band * spread_px * 0.20, path[2][1] + abs(band) * 17.0),
        )
        draw_wisp_segments(
            draw,
            shifted,
            max(0.0, head - 0.82),
            head,
            0.0,
            0.0,
            (65, 142, 151, round((48 + index * 6) * scale)),
            4 if abs(band) < 0.2 else 3,
            (index - 2) * 0.018,
        )


def draw_exhale_carrier(
    layer: Image.Image,
    progress: float,
    path: tuple[tuple[float, float], ...],
    scale: float,
) -> None:
    draw = ImageDraw.Draw(layer)
    head = progress
    tail = max(0.0, head - 0.46)
    offsets = (-25.0, -8.0, 10.0, 27.0) if scale >= 0.9 else (-15.0, 4.0, 22.0)
    for index, offset_y in enumerate(offsets):
        draw_wisp_segments(
            draw,
            path,
            tail,
            head,
            5.0 * math.sin(index * 1.7),
            offset_y,
            (62, 143, 153, round((50 + index * 6) * scale)),
            4 if index == 1 else 3,
            (index - 1) * 0.021,
        )
    for index in range(18):
        u = max(tail, head - index * 0.021)
        x, y = quadratic_point(path, u)
        radius = 1 + index % 3
        draw.ellipse(
            (x - radius, y + 18 + index % 4, x + radius, y + 18 + index % 4 + radius),
            fill=(188, 169, 127, round((42 - index) * scale)),
        )


def flow_layer(
    t_s: float,
    config: dict[str, object],
    carrier: str,
) -> tuple[Image.Image, dict[str, float | str]]:
    geometry = config["geometry"]
    lag_s = float(config["timeline"]["actual_lag_s"])
    phase, progress = phase_state(t_s) if carrier == "target" else actual_state(t_s, lag_s)
    inhale_path = tuple(tuple(float(v) for v in point) for point in geometry[f"{carrier}_inhale_path"])
    exhale_path = tuple(tuple(float(v) for v in point) for point in geometry[f"{carrier}_exhale_path"])
    spread = float(geometry[f"{carrier}_inhale_spread_px"])
    scale = 1.0 if carrier == "target" else 0.82
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    if phase == "INHALE":
        draw_inhale_carrier(layer, progress, inhale_path, spread, scale)
    else:
        residual = max(0.0, 1.0 - progress / 0.26)
        if residual > 0.0:
            draw_inhale_carrier(layer, 1.0, inhale_path, spread, scale * residual)
        draw_exhale_carrier(layer, progress, exhale_path, scale)
    glow = layer.filter(ImageFilter.GaussianBlur(8 if carrier == "target" else 6))
    combined = Image.alpha_composite(glow, layer)
    feather = 54 if carrier == "target" else 40
    return clip_layer(combined, geometry[f"{carrier}_bounds"], feather), {
        "phase": phase,
        "progress": progress,
        "max_opacity": 68.0 * scale,
    }


def ring_radius(phase: str, progress: float, minimum: float, maximum: float) -> float:
    return minimum + (maximum - minimum) * progress if phase == "INHALE" else maximum - (maximum - minimum) * progress


def abstract_layer(t_s: float, config: dict[str, object]) -> tuple[Image.Image, dict[str, object]]:
    target_phase, target_progress = phase_state(t_s)
    actual_phase, actual_progress = actual_state(t_s, float(config["timeline"]["actual_lag_s"]))
    center_x, center_y = 960, 540
    outer_radius = ring_radius(target_phase, target_progress, 92.0, 154.0)
    inner_radius = ring_radius(actual_phase, actual_progress, 61.0, 104.0)
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        (center_x - outer_radius, center_y - outer_radius, center_x + outer_radius, center_y + outer_radius),
        outline=(76, 162, 166, 220),
        width=8,
    )
    draw.ellipse(
        (center_x - inner_radius, center_y - inner_radius, center_x + inner_radius, center_y + inner_radius),
        outline=(220, 198, 151, 192),
        width=6,
    )
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    combined = Image.alpha_composite(glow, layer)
    return clip_layer(combined, config["geometry"]["abstract_bounds"], 24), {
        "target_phase": target_phase,
        "target_progress": target_progress,
        "target_radius": outer_radius,
        "actual_phase": actual_phase,
        "actual_progress": actual_progress,
        "actual_radius": inner_radius,
    }


def participant_frames(
    environment: Image.Image,
    t_s: float,
    config: dict[str, object],
) -> tuple[Image.Image, Image.Image, dict[str, object]]:
    target, target_metrics = flow_layer(t_s, config, "target")
    actual, actual_metrics = flow_layer(t_s, config, "actual")
    rings, ring_metrics = abstract_layer(t_s, config)
    scene = Image.alpha_composite(environment.convert("RGBA"), target)
    scene = Image.alpha_composite(scene, actual).convert("RGB")
    abstract = Image.alpha_composite(environment.convert("RGBA"), rings).convert("RGB")
    return scene, abstract, {"target": target_metrics, "actual": actual_metrics, "rings": ring_metrics}


def review_frame(scene: Image.Image, abstract: Image.Image, t_s: float, metrics: dict[str, object]) -> Image.Image:
    canvas = Image.new("RGB", (3840, 1200), (28, 27, 24))
    canvas.paste(scene, (0, 120))
    canvas.paste(abstract, (1920, 120))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(24)
    target = metrics["target"]
    actual = metrics["actual"]
    draw.text((36, 18), "V-04 H3 INPUT / HEAT / CANDIDATE-V1", font=title_font, fill=(244, 244, 240))
    draw.text(
        (36, 68),
        f"t={t_s:05.2f}s  target={target['phase']}  actual={actual['phase']}  shared scroll/haze/audio",
        font=label_font,
        fill=(201, 201, 194),
    )
    draw.text((1390, 68), "SCENE_NATIVE", font=label_font, fill=(116, 190, 184))
    draw.text((3300, 68), "ABSTRACT_PACER", font=label_font, fill=(196, 177, 145))
    return canvas


def cue_difference_mask(config: dict[str, object]) -> np.ndarray:
    mask = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(mask)
    for key in ("target_bounds", "actual_bounds", "abstract_bounds"):
        draw.rectangle(tuple(config["geometry"][key]), fill=255)
    margin = int(config["machine_gates"]["difference_mask_glow_margin_px"])
    mask = mask.filter(ImageFilter.MaxFilter(margin * 2 + 1))
    return np.asarray(mask, dtype=np.uint8) > 0


def make_heat_audio(path: Path, sample_rate: int, duration_s: float) -> None:
    rng = np.random.default_rng(30083029)
    count = round(sample_rate * duration_s)
    time = np.arange(count, dtype=np.float64) / sample_rate
    left_noise = rng.normal(0.0, 1.0, count)
    right_noise = rng.normal(0.0, 1.0, count)
    left = 0.54 * moving_average(left_noise, 180) + 0.31 * moving_average(left_noise, 1450) + 0.15 * moving_average(left_noise, 6100)
    right = 0.51 * moving_average(right_noise, 220) + 0.34 * moving_average(right_noise, 1700) + 0.15 * moving_average(right_noise, 5600)
    air = 0.10 * np.sin(math.tau * 0.043 * time + 0.4) + 0.07 * np.sin(math.tau * 0.077 * time + 1.8)
    stereo = np.column_stack((left + air, right + 0.94 * air))
    stereo /= max(1e-9, float(np.max(np.abs(stereo))))
    write_pcm24(path, stereo * 0.27, sample_rate)


def make_keyframe_sheet(
    frames: list[tuple[float, Image.Image]],
    output: Path,
    grayscale: bool,
    lag_s: float,
) -> None:
    canvas = Image.new("RGB", (1920, 1400), (27, 26, 23))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(22)
    title = "V-04 H3 / HEAT / GRAYSCALE GEOMETRY" if grayscale else "V-04 H3 / HEAT / KEYFRAME REVIEW"
    draw.text((38, 22), title, font=title_font, fill=(245, 245, 241))
    for index, (t_s, frame) in enumerate(frames):
        column = index % 2
        row = index // 2
        x = 35 + column * 950
        y = 82 + row * 325
        thumbnail = frame.resize((900, 281), Image.Resampling.LANCZOS)
        if grayscale:
            thumbnail = thumbnail.convert("L").convert("RGB")
        canvas.paste(thumbnail, (x, y + 28))
        target_phase, _ = phase_state(t_s)
        actual_phase, _ = actual_state(t_s, lag_s)
        draw.text((x, y), f"t={t_s:04.1f}s  target={target_phase}  actual={actual_phase}", font=label_font, fill=(224, 225, 220))
        draw.rectangle((x, y + 28, x + 900, y + 309), outline=(220, 220, 214), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def geometry_metrics(config: dict[str, object]) -> dict[str, object]:
    geometry = config["geometry"]
    inhale_path = tuple(tuple(float(v) for v in point) for point in geometry["target_inhale_path"])
    exhale_path = tuple(tuple(float(v) for v in point) for point in geometry["target_exhale_path"])
    inhale_length = quadratic_length(inhale_path)
    exhale_length = quadratic_length(exhale_path)
    return {
        "inhale_path_length_px": inhale_length,
        "exhale_path_length_px": exhale_length,
        "exhale_to_inhale_path_ratio": exhale_length / inhale_length,
        "inhale_rise_px": inhale_path[0][1] - inhale_path[2][1],
        "exhale_forward_travel_px": exhale_path[2][0] - exhale_path[0][0],
        "inhale_max_opacity": 68.0,
        "exhale_max_opacity": 68.0,
        "target_at_4s": phase_state(4.0)[0],
        "actual_at_4s": actual_state(4.0, float(config["timeline"]["actual_lag_s"]))[0],
    }


def render_preflight(plate: Image.Image, config: dict[str, object]) -> None:
    output = REPO / ".artifacts-local/V-04/H3/heat-preflight-v1"
    output.mkdir(parents=True, exist_ok=True)
    for t_s in (0.0, 2.0, 3.9, 4.3, 6.0, 8.0, 9.9):
        environment, _ = shared_environment(plate, t_s, config)
        scene, abstract, metrics = participant_frames(environment, t_s, config)
        review_frame(scene, abstract, t_s, metrics).save(output / f"heat-preflight-{t_s:04.1f}.png")
    print(f"PASS: heat preflight frames written to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    h2 = json.loads(H2_REVIEW.read_text(encoding="utf-8"))
    require(config["schema_version"] == "1.0", "heat config schema drift")
    require(config["technical_id"] == "heat" and config["preview_id"] == "heat-candidate-v1", "heat identity drift")
    require(h2["decision"] == "PASS" and h2["results"]["H2"] == "PASS", "H2 has not passed")
    require(any(item["candidate_id"] == "heat-A" for item in h1["selections"]), "heat-A is not H1 selected")
    source = REPO / config["source"]["panorama_file"]
    contract = HERE / config["design_contract"]
    require(source.is_file() and contract.is_file(), "heat source or design contract missing")
    require(sha256(source) == config["source"]["panorama_sha256"], "heat source hash mismatch")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools are missing")
    with Image.open(source) as image:
        source_size = image.size
        plate = prepare_scroll_plate(image, int(config["camera"]["source_plate_height_px"]))
    if args.preflight:
        render_preflight(plate, config)
        return

    output_root = REPO / config["outputs"]["artifact_root"]
    require(not output_root.exists(), f"heat candidate output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    fps = int(config["timeline"]["fps"])
    frame_count = int(config["timeline"]["frame_count"])
    duration_s = float(config["timeline"]["duration_s"])
    keyframe_indices = {round(float(t) * fps): float(t) for t in config["keyframe_times_s"]}
    keyframes: list[tuple[float, Image.Image]] = []
    difference_mask = cue_difference_mask(config)
    max_outside_difference = 0
    metrics = geometry_metrics(config)

    with tempfile.TemporaryDirectory(prefix="heat-candidate-v1-build-", dir=output_root.parent) as temporary:
        build = Path(temporary)
        silent_scene = build / "scene-silent.mp4"
        silent_abstract = build / "abstract-silent.mp4"
        silent_review = build / "review-silent.mp4"
        logs = [build / "scene.log", build / "abstract.log", build / "review.log"]
        encoders = (
            open_video_encoder(ffmpeg, silent_scene, SIZE, fps, logs[0]),
            open_video_encoder(ffmpeg, silent_abstract, SIZE, fps, logs[1]),
            open_video_encoder(ffmpeg, silent_review, (3840, 1200), fps, logs[2]),
        )
        final_displacement = 0.0
        try:
            for frame_index in range(frame_count):
                t_s = frame_index / fps
                environment, final_displacement = shared_environment(plate, t_s, config)
                scene, abstract, frame_metrics = participant_frames(environment, t_s, config)
                review = review_frame(scene, abstract, t_s, frame_metrics)
                scene_array = np.asarray(scene, dtype=np.int16)
                abstract_array = np.asarray(abstract, dtype=np.int16)
                outside = np.abs(scene_array - abstract_array)[~difference_mask]
                if outside.size:
                    max_outside_difference = max(max_outside_difference, int(outside.max()))
                encoders[0].stdin.write(scene.tobytes())
                encoders[1].stdin.write(abstract.tobytes())
                encoders[2].stdin.write(review.tobytes())
                if frame_index in keyframe_indices:
                    keyframes.append((keyframe_indices[frame_index], review.copy()))
        finally:
            for encoder in encoders:
                if encoder.stdin:
                    encoder.stdin.close()
            for encoder in encoders:
                require(encoder.wait() == 0, "heat video encoder failed")

        raw_audio = build / "heat-ambient-raw.wav"
        ambient = build / config["outputs"]["ambient_audio"]
        make_heat_audio(raw_audio, int(config["audio"]["sample_rate_hz"]), duration_s)
        normalize_audio(ffmpeg, raw_audio, ambient)
        final_scene = build / config["outputs"]["scene_native_video"]
        final_abstract = build / config["outputs"]["abstract_pacer_video"]
        final_review = build / config["outputs"]["paired_review_video"]
        mux(ffmpeg, silent_scene, ambient, final_scene)
        mux(ffmpeg, silent_abstract, ambient, final_abstract)
        mux(ffmpeg, silent_review, ambient, final_review)
        for path in (raw_audio, silent_scene, silent_abstract, silent_review, *logs):
            path.unlink(missing_ok=True)

        review_keyframes = HERE / config["outputs"]["review_keyframes"]
        grayscale_keyframes = HERE / config["outputs"]["grayscale_keyframes"]
        lag_s = float(config["timeline"]["actual_lag_s"])
        make_keyframe_sheet(keyframes, review_keyframes, grayscale=False, lag_s=lag_s)
        make_keyframe_sheet(keyframes, grayscale_keyframes, grayscale=True, lag_s=lag_s)
        probes = {
            "scene_native": ffprobe(ffprobe_path, final_scene),
            "abstract_pacer": ffprobe(ffprobe_path, final_abstract),
            "paired_review": ffprobe(ffprobe_path, final_review),
            "ambient_audio": ffprobe(ffprobe_path, ambient),
        }
        manifest = {
            "schema_version": "1.0",
            "task_id": "V-04",
            "gate_id": "H3_INPUT_PREVIEWS",
            "preview_id": config["preview_id"],
            "technical_id": "heat",
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "design_contract_sha256": sha256(contract),
            "h1_selection_sha256": sha256(H1_SELECTION),
            "h2_review_sha256": sha256(H2_REVIEW),
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
                "inhale_duration_s": float(config["timeline"]["inhale_duration_s"]),
                "exhale_duration_s": float(config["timeline"]["exhale_duration_s"]),
                "phase_slots": config["timeline"]["phase_slots"],
                "actual_lag_s": lag_s,
                "recovery_value": float(config["timeline"]["recovery_value"]),
                "scroll_speed_viewport_per_s": float(config["camera"]["scroll_speed_viewport_per_s"]),
                "final_displacement_px": final_displacement,
                "background_phase_inputs": [],
                "max_raw_difference_outside_expected_mask": max_outside_difference,
                "geometry_metrics": metrics,
            },
            "audio_metrics": audio_metrics(ffmpeg, ambient),
            "outputs": {
                "scene_native": media_entry(final_scene, probes["scene_native"]),
                "abstract_pacer": media_entry(final_abstract, probes["abstract_pacer"]),
                "paired_review": media_entry(final_review, probes["paired_review"]),
                "ambient_audio": media_entry(ambient, probes["ambient_audio"]),
                "review_keyframes": {
                    "file": review_keyframes.relative_to(HERE).as_posix(),
                    "size_bytes": review_keyframes.stat().st_size,
                    "sha256": sha256(review_keyframes),
                    "width": 1920,
                    "height": 1400,
                },
                "grayscale_keyframes": {
                    "file": grayscale_keyframes.relative_to(HERE).as_posix(),
                    "size_bytes": grayscale_keyframes.stat().st_size,
                    "sha256": sha256(grayscale_keyframes),
                    "width": 1920,
                    "height": 1400,
                },
            },
            "asset_status": {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False},
            "gate_status": "MACHINE_VALIDATION_PENDING",
            "next_if_pass": "continue snow and corridor input previews before H3 assembly",
            "evidence_boundary": "The preview is design evidence only; Unity runtime, formal build and device chain remain unverified.",
        }
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PASS: rendered heat-candidate-v1; 300 shared frames; "
        f"4-second inhale and 6-second exhale; outside-mask diff={max_outside_difference}"
    )


if __name__ == "__main__":
    main()
