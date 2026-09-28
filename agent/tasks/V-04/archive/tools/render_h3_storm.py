from __future__ import annotations

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
CONFIG_PATH = HERE / "V-04_H3_storm样片配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
H2_REVIEW = HERE / "V-04_H2人工评审记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3_storm候选清单_v1.0.json"
SIZE = (1920, 1080)


def phase_state(t_s: float) -> tuple[str, float, float]:
    phase_duration = 3.0
    slots = ("INHALE", "HOLD_1", "EXHALE", "HOLD_2")
    index = min(3, max(0, int(t_s // phase_duration)))
    progress = smoothstep((t_s - index * phase_duration) / phase_duration)
    if index == 0:
        openness = progress
    elif index == 1:
        openness = 1.0
    elif index == 2:
        openness = 1.0 - progress
    else:
        openness = 0.0
    return slots[index], progress, openness


def actual_state(t_s: float, lag_s: float) -> tuple[str, float, float]:
    return phase_state(max(0.0, t_s - lag_s))


def prepare_scroll_plate(source: Image.Image, target_height: int) -> Image.Image:
    source = source.convert("RGB")
    target_width = round(source.width * target_height / source.height)
    require(target_width >= 2381, "storm source plate is too narrow for the frozen scroll")
    return source.resize((target_width, target_height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def rain_streaks() -> tuple[tuple[float, float, float, float, int], ...]:
    rng = np.random.default_rng(290829)
    streaks = []
    for _ in range(310):
        streaks.append(
            (
                float(rng.uniform(-180.0, 2100.0)),
                float(rng.uniform(-160.0, 1120.0)),
                float(rng.uniform(20.0, 72.0)),
                float(rng.uniform(175.0, 470.0)),
                int(rng.integers(18, 54)),
            )
        )
    return tuple(streaks)


def draw_shared_rain(t_s: float) -> Image.Image:
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x0, y0, length, speed, alpha in rain_streaks():
        y = (y0 + speed * t_s) % 1280.0 - 160.0
        x = (x0 + speed * 0.083 * t_s) % 2280.0 - 180.0
        draw.line((x, y, x + length * 0.25, y + length), fill=(196, 215, 224, alpha), width=2)
    return overlay.filter(ImageFilter.GaussianBlur(0.35))


def shared_environment(plate: Image.Image, t_s: float, config: dict[str, object]) -> tuple[Image.Image, float]:
    speed = float(config["camera"]["scroll_speed_viewport_per_s"])
    displacement = speed * SIZE[0] * t_s
    crop_y = int(config["camera"]["vertical_crop_y_px"])
    crop_x = min(plate.width - SIZE[0], int(round(displacement)))
    frame = plate.crop((crop_x, crop_y, crop_x + SIZE[0], crop_y + SIZE[1]))
    frame = ImageEnhance.Contrast(frame).enhance(0.98)
    frame = ImageEnhance.Brightness(frame).enhance(1.015)

    fog = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    fog_draw = ImageDraw.Draw(fog)
    for index in range(6):
        x = -260 + index * 430 + 90 * math.sin(0.17 * t_s + index * 1.31)
        y = 330 + index * 65 + 22 * math.sin(0.11 * t_s + index * 0.77)
        fog_draw.ellipse((x, y, x + 720, y + 250), fill=(199, 211, 217, 15))
    fog = fog.filter(ImageFilter.GaussianBlur(72))
    environment = Image.alpha_composite(frame.convert("RGBA"), fog)
    environment = Image.alpha_composite(environment, draw_shared_rain(t_s)).convert("RGB")
    return environment, float(crop_x)


def gate_geometry(openness: float, config: dict[str, object]) -> dict[str, float]:
    geometry = config["geometry"]
    half_width = float(geometry["neutral_half_width_px"]) + (
        float(geometry["maximum_half_width_px"]) - float(geometry["neutral_half_width_px"])
    ) * openness
    top_y = float(geometry["neutral_top_y"]) + (
        float(geometry["maximum_top_y"]) - float(geometry["neutral_top_y"])
    ) * openness
    return {"half_width": half_width, "top_y": top_y}


def clip_layer(layer: Image.Image, bounds: list[int], feather_px: int = 0) -> Image.Image:
    left, top, right, bottom = (int(value) for value in bounds)
    clip_values = np.zeros((SIZE[1], SIZE[0]), dtype=np.float32)
    if feather_px <= 0:
        clip_values[top : bottom + 1, left : right + 1] = 1.0
    else:
        y, x = np.mgrid[top : bottom + 1, left : right + 1]
        distance = np.minimum.reduce((x - left, right - x, y - top, bottom - y)).astype(np.float32)
        u = np.clip(distance / feather_px, 0.0, 1.0)
        clip_values[top : bottom + 1, left : right + 1] = u * u * (3.0 - 2.0 * u)
    clip = Image.fromarray(np.round(clip_values * 255).astype(np.uint8), mode="L")
    clipped = layer.copy()
    clipped.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
    return clipped


def gate_boundary_points(openness: float, config: dict[str, object]) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    geometry = config["geometry"]
    values = gate_geometry(openness, config)
    center_x = float(geometry["gate_center_x"])
    base_y = float(geometry["gate_base_y"])
    top_y = values["top_y"]
    points_left: list[tuple[float, float]] = []
    points_right: list[tuple[float, float]] = []
    for y in np.linspace(top_y, base_y, 44):
        u = (y - top_y) / max(1.0, base_y - top_y)
        width = 20.0 + (values["half_width"] - 20.0) * math.pow(u, 0.58)
        points_left.append((center_x - width, float(y)))
        points_right.append((center_x + width, float(y)))
    return points_left, points_right


def gate_layer(t_s: float, config: dict[str, object], dynamic: bool) -> tuple[Image.Image, dict[str, float]]:
    phase, progress, openness = phase_state(t_s)
    if not dynamic:
        phase, progress, openness = "NEUTRAL", 0.0, 0.0
    geometry = gate_geometry(openness, config)
    left, right = gate_boundary_points(openness, config)

    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    mist = Image.new("L", SIZE, 0)
    mist_draw = ImageDraw.Draw(mist)
    target_bounds = tuple(int(value) for value in config["geometry"]["target_bounds"])
    top_y = geometry["top_y"]
    base_y = float(config["geometry"]["gate_base_y"])
    left_polygon = [
        (target_bounds[0], top_y - 35),
        (left[0][0], left[0][1]),
        *left,
        (target_bounds[0], base_y + 30),
    ]
    right_polygon = [
        (right[0][0], right[0][1]),
        (target_bounds[2], top_y - 35),
        (target_bounds[2], base_y + 30),
        *reversed(right),
    ]
    curtain_alpha = 96 if dynamic else 54
    mist_draw.polygon(left_polygon, fill=curtain_alpha)
    mist_draw.polygon(right_polygon, fill=curtain_alpha)
    mist = mist.filter(ImageFilter.GaussianBlur(18))
    curtain = Image.new("RGBA", SIZE, (157, 187, 202, 0))
    curtain.putalpha(mist)
    layer = Image.alpha_composite(layer, curtain)

    streaks = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    streak_draw = ImageDraw.Draw(streaks)
    for index in range(46):
        x = target_bounds[0] + ((index * 97 + int(t_s * 41)) % (target_bounds[2] - target_bounds[0]))
        y = target_bounds[1] + ((index * 61 + int(t_s * (93 + index % 7))) % 500)
        streak_draw.line((x, y, x + 12, y + 48), fill=(190, 219, 229, 118 if dynamic else 66), width=2)
    streaks.putalpha(ImageChops.multiply(streaks.getchannel("A"), mist))
    layer = Image.alpha_composite(layer, streaks)

    edge_mist = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    edge_mist_draw = ImageDraw.Draw(edge_mist)
    for boundary in (left, right):
        for index, (x, y) in enumerate(boundary):
            if index % 5 == 0:
                edge_mist_draw.ellipse(
                    (x - 44, y - 27, x + 48, y + 31),
                    fill=(186, 211, 217, 31 if dynamic else 17),
                )
    layer = Image.alpha_composite(layer, edge_mist.filter(ImageFilter.GaussianBlur(23)))

    if dynamic and phase == "EXHALE":
        flow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        flow_draw = ImageDraw.Draw(flow)
        shift = 160 * progress
        for index in range(4):
            start_x = 1220 + index * 78 + shift
            start_y = 470 + index * 34 + 95 * progress
            flow_draw.arc(
                (start_x - 120, start_y - 80, start_x + 260, start_y + 170),
                210,
                330,
                fill=(160, 218, 220, 115),
                width=5,
            )
        layer = Image.alpha_composite(layer, flow.filter(ImageFilter.GaussianBlur(1.2)))

    return clip_layer(layer, config["geometry"]["target_bounds"], feather_px=70), {
        "phase": phase,
        "progress": progress,
        "openness": openness,
        **geometry,
    }


def bezier(points: tuple[tuple[float, float], ...], u: float) -> tuple[float, float]:
    if len(points) == 3:
        one = 1.0 - u
        return (
            one * one * points[0][0] + 2 * one * u * points[1][0] + u * u * points[2][0],
            one * one * points[0][1] + 2 * one * u * points[1][1] + u * u * points[2][1],
        )
    raise ValueError("quadratic bezier expected")


def actual_layer(t_s: float, config: dict[str, object]) -> tuple[Image.Image, dict[str, float | str]]:
    lag_s = float(config["timeline"]["actual_lag_s"])
    phase, progress, openness = actual_state(t_s, lag_s)
    if phase in {"INHALE", "HOLD_1"}:
        path = ((510.0, 575.0), (665.0, 445.0), (850.0, 390.0))
        head = progress if phase == "INHALE" else 1.0
    else:
        path = ((850.0, 390.0), (815.0, 515.0), (625.0, 590.0))
        head = progress if phase == "EXHALE" else 1.0

    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    tail = max(0.0, head - 0.19)
    samples = np.linspace(tail, max(tail, head), 72)
    for offset_index, offset in enumerate((-18.0, 0.0, 19.0)):
        points = [bezier(path, float(u)) for u in samples]
        shifted = [
            (
                x + 4.0 * math.sin(float(u) * math.tau + offset_index * 1.7),
                y + offset + 3.0 * math.sin(float(u) * math.tau * 1.5 + offset_index),
            )
            for (x, y), u in zip(points, samples)
        ]
        draw.line(shifted, fill=(226, 231, 211, 68 + offset_index * 10), width=3, joint="curve")
    glow = layer.filter(ImageFilter.GaussianBlur(9))
    return clip_layer(Image.alpha_composite(glow, layer), config["geometry"]["actual_bounds"], feather_px=36), {
        "phase": phase,
        "progress": progress,
        "openness": openness,
        "head_u": head,
    }


def abstract_layer(t_s: float, config: dict[str, object]) -> tuple[Image.Image, dict[str, object]]:
    target_phase, target_progress, target_open = phase_state(t_s)
    actual_phase, actual_progress, actual_open = actual_state(t_s, float(config["timeline"]["actual_lag_s"]))
    center_x, center_y = 960, 540
    outer_radius = 110 + 44 * target_open
    inner_radius = 72 + 32 * actual_open
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        (center_x - outer_radius, center_y - outer_radius, center_x + outer_radius, center_y + outer_radius),
        outline=(112, 191, 181, 215),
        width=8,
    )
    draw.ellipse(
        (center_x - inner_radius, center_y - inner_radius, center_x + inner_radius, center_y + inner_radius),
        outline=(235, 225, 196, 188),
        width=6,
    )
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    return clip_layer(Image.alpha_composite(glow, layer), config["geometry"]["abstract_bounds"]), {
        "target_phase": target_phase,
        "target_progress": target_progress,
        "target_radius": outer_radius,
        "actual_phase": actual_phase,
        "actual_progress": actual_progress,
        "actual_radius": inner_radius,
    }


def participant_frames(environment: Image.Image, t_s: float, config: dict[str, object]) -> tuple[Image.Image, Image.Image, dict[str, object]]:
    target, target_metrics = gate_layer(t_s, config, dynamic=True)
    actual, actual_metrics = actual_layer(t_s, config)
    neutral_gate, _ = gate_layer(t_s, config, dynamic=False)
    rings, ring_metrics = abstract_layer(t_s, config)
    scene = Image.alpha_composite(environment.convert("RGBA"), target)
    scene = Image.alpha_composite(scene, actual).convert("RGB")
    abstract = Image.alpha_composite(environment.convert("RGBA"), neutral_gate)
    abstract = Image.alpha_composite(abstract, rings).convert("RGB")
    return scene, abstract, {"target": target_metrics, "actual": actual_metrics, "rings": ring_metrics}


def review_frame(scene: Image.Image, abstract: Image.Image, t_s: float, metrics: dict[str, object]) -> Image.Image:
    canvas = Image.new("RGB", (3840, 1200), (19, 24, 29))
    canvas.paste(scene, (0, 120))
    canvas.paste(abstract, (1920, 120))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(24)
    target = metrics["target"]
    actual = metrics["actual"]
    draw.text((36, 18), "V-04 H3 INPUT / STORM / CANDIDATE-V1", font=title_font, fill=(244, 244, 244))
    draw.text(
        (36, 68),
        f"t={t_s:05.2f}s  target={target['phase']}  actual={actual['phase']}  shared scroll/weather/audio",
        font=label_font,
        fill=(195, 202, 208),
    )
    draw.text((1390, 68), "SCENE_NATIVE", font=label_font, fill=(158, 211, 202))
    draw.text((3300, 68), "ABSTRACT_PACER", font=label_font, fill=(190, 177, 220))
    return canvas


def cue_difference_mask(config: dict[str, object]) -> np.ndarray:
    mask = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(mask)
    for key in ("target_bounds", "actual_bounds", "abstract_bounds"):
        draw.rectangle(tuple(config["geometry"][key]), fill=255)
    margin = int(config["machine_gates"]["difference_mask_glow_margin_px"])
    mask = mask.filter(ImageFilter.MaxFilter(margin * 2 + 1))
    return np.asarray(mask, dtype=np.uint8) > 0


def make_storm_audio(path: Path, sample_rate: int, duration_s: float) -> None:
    rng = np.random.default_rng(29082917)
    count = round(sample_rate * duration_s)
    time = np.arange(count, dtype=np.float64) / sample_rate
    left_noise = rng.normal(0.0, 1.0, count)
    right_noise = rng.normal(0.0, 1.0, count)
    left = 0.46 * moving_average(left_noise, 24) + 0.34 * moving_average(left_noise, 170) + 0.20 * moving_average(left_noise, 2600)
    right = 0.44 * moving_average(right_noise, 29) + 0.36 * moving_average(right_noise, 190) + 0.20 * moving_average(right_noise, 2300)
    wind = 0.16 * np.sin(math.tau * 0.071 * time + 0.7) + 0.10 * np.sin(math.tau * 0.113 * time + 2.1)
    stereo = np.column_stack((left + wind, right + 0.92 * wind))
    stereo /= max(1e-9, float(np.max(np.abs(stereo))))
    write_pcm24(path, stereo * 0.30, sample_rate)


def make_keyframe_sheet(frames: list[tuple[float, Image.Image]], output: Path, grayscale: bool) -> None:
    canvas = Image.new("RGB", (1920, 1400), (20, 23, 27))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(22)
    title = "V-04 H3 / STORM / GRAYSCALE GEOMETRY" if grayscale else "V-04 H3 / STORM / KEYFRAME REVIEW"
    draw.text((38, 22), title, font=title_font, fill=(245, 245, 245))
    for index, (t_s, frame) in enumerate(frames):
        column = index % 2
        row = index // 2
        x = 35 + column * 950
        y = 82 + row * 325
        thumbnail = frame.resize((900, 281), Image.Resampling.LANCZOS)
        if grayscale:
            thumbnail = thumbnail.convert("L").convert("RGB")
        canvas.paste(thumbnail, (x, y + 28))
        target_phase, _, _ = phase_state(t_s)
        actual_phase, _, _ = actual_state(t_s, 0.55)
        draw.text((x, y), f"t={t_s:04.1f}s  target={target_phase}  actual={actual_phase}", font=label_font, fill=(222, 226, 229))
        draw.rectangle((x, y + 28, x + 900, y + 309), outline=(220, 220, 220), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def geometry_metrics(config: dict[str, object]) -> dict[str, object]:
    neutral = gate_geometry(0.0, config)
    maximum = gate_geometry(1.0, config)
    hold_1_a = gate_geometry(phase_state(3.4)[2], config)
    hold_1_b = gate_geometry(phase_state(5.6)[2], config)
    hold_2_a = gate_geometry(phase_state(9.4)[2], config)
    hold_2_b = gate_geometry(phase_state(11.6)[2], config)
    return {
        "neutral_half_width_px": neutral["half_width"],
        "maximum_half_width_px": maximum["half_width"],
        "half_width_expansion_px": maximum["half_width"] - neutral["half_width"],
        "hold_1_geometry_drift_px": max(
            abs(hold_1_a["half_width"] - hold_1_b["half_width"]),
            abs(hold_1_a["top_y"] - hold_1_b["top_y"]),
        ),
        "hold_2_geometry_drift_px": max(
            abs(hold_2_a["half_width"] - hold_2_b["half_width"]),
            abs(hold_2_a["top_y"] - hold_2_b["top_y"]),
        ),
        "target_at_3s": phase_state(3.0)[0],
        "actual_at_3s": actual_state(3.0, float(config["timeline"]["actual_lag_s"]))[0],
        "target_at_9s": phase_state(9.0)[0],
        "actual_at_9s": actual_state(9.0, float(config["timeline"]["actual_lag_s"]))[0],
    }


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    h2 = json.loads(H2_REVIEW.read_text(encoding="utf-8"))
    require(config["schema_version"] == "1.0", "storm config schema drift")
    require(config["technical_id"] == "storm" and config["preview_id"] == "storm-candidate-v1", "storm identity drift")
    require(h2["decision"] == "PASS" and h2["results"]["H2"] == "PASS", "H2 has not passed")
    require(any(item["candidate_id"] == "storm-A" for item in h1["selections"]), "storm-A is not H1 selected")
    source = REPO / config["source"]["panorama_file"]
    contract = HERE / config["design_contract"]
    require(source.is_file() and contract.is_file(), "storm source or design contract missing")
    require(sha256(source) == config["source"]["panorama_sha256"], "storm source hash mismatch")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools are missing")

    output_root = REPO / config["outputs"]["artifact_root"]
    require(not output_root.exists(), f"storm candidate output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    fps = int(config["timeline"]["fps"])
    frame_count = int(config["timeline"]["frame_count"])
    duration_s = float(config["timeline"]["duration_s"])
    keyframe_indices = {round(float(t) * fps): float(t) for t in config["keyframe_times_s"]}
    keyframes: list[tuple[float, Image.Image]] = []
    difference_mask = cue_difference_mask(config)
    max_outside_difference = 0
    metrics = geometry_metrics(config)

    with tempfile.TemporaryDirectory(prefix="storm-candidate-v1-build-", dir=output_root.parent) as temporary:
        build = Path(temporary)
        with Image.open(source) as image:
            source_size = image.size
            plate = prepare_scroll_plate(image, int(config["camera"]["source_plate_height_px"]))
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
                require(encoder.wait() == 0, "storm video encoder failed")

        raw_audio = build / "storm-ambient-raw.wav"
        ambient = build / config["outputs"]["ambient_audio"]
        make_storm_audio(raw_audio, int(config["audio"]["sample_rate_hz"]), duration_s)
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
        make_keyframe_sheet(keyframes, review_keyframes, grayscale=False)
        make_keyframe_sheet(keyframes, grayscale_keyframes, grayscale=True)
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
            "technical_id": "storm",
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
                "phase_duration_s": float(config["timeline"]["phase_duration_s"]),
                "phase_slots": config["timeline"]["phase_slots"],
                "actual_lag_s": float(config["timeline"]["actual_lag_s"]),
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
            "next_if_pass": "continue heat, snow and corridor input previews before H3 assembly",
            "evidence_boundary": "The preview is design evidence only; Unity runtime, formal build and device chain remain unverified.",
        }
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PASS: rendered storm-candidate-v1; 360 shared frames; "
        f"four 3-second phases; outside-mask diff={max_outside_difference}"
    )


if __name__ == "__main__":
    main()
