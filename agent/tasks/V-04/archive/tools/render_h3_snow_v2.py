from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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
CONFIG_PATH = HERE / "V-04_H3_snow样片配置_v2.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
BACKGROUND_SELECTION = HERE / "V-04_H3_R2背景选择记录_v1.0.json"
H2_REVIEW = HERE / "V-04_H2_candidate-v11人工评审记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3_snow候选清单_v2.0.json"
SIZE = (1920, 1080)


def phase_state(t_s: float) -> tuple[str, float]:
    if t_s < 5.0:
        return "INHALE", smoothstep(max(0.0, t_s) / 5.0)
    return "EXHALE", smoothstep(min(1.0, max(0.0, t_s - 5.0) / 5.0))


def actual_state(t_s: float, lag_s: float) -> tuple[str, float]:
    return phase_state(max(0.0, t_s - lag_s))


def motion_state(phase: str, progress: float) -> float:
    return progress if phase == "INHALE" else 1.0 - progress


def prepare_fixed_plate(source: Image.Image) -> Image.Image:
    return ImageOps.fit(
        source.convert("RGB"),
        SIZE,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


@lru_cache(maxsize=1)
def ambient_flakes() -> tuple[tuple[float, float, float, float, float, int], ...]:
    rng = np.random.default_rng(30083041)
    flakes = []
    for _ in range(128):
        flakes.append(
            (
                float(rng.uniform(-90.0, 2010.0)),
                float(rng.uniform(-60.0, 1140.0)),
                float(rng.uniform(11.0, 28.0)),
                float(rng.uniform(-7.0, 8.0)),
                float(rng.uniform(0.8, 2.1)),
                int(rng.integers(22, 60)),
            )
        )
    return tuple(flakes)


@lru_cache(maxsize=1)
def fog_bands() -> tuple[tuple[float, float, float, float, int], ...]:
    rng = np.random.default_rng(30083043)
    bands = []
    for _ in range(5):
        bands.append(
            (
                float(rng.uniform(-600.0, 1900.0)),
                float(rng.uniform(350.0, 790.0)),
                float(rng.uniform(650.0, 980.0)),
                float(rng.uniform(2.0, 5.5)),
                int(rng.integers(8, 17)),
            )
        )
    return tuple(bands)


def draw_shared_weather(t_s: float) -> Image.Image:
    fog = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    fog_draw = ImageDraw.Draw(fog)
    for x0, y0, width, speed, alpha in fog_bands():
        x = x0 + speed * t_s
        for repeat in (-2300.0, 0.0, 2300.0):
            fog_draw.ellipse(
                (x + repeat - width, y0 - 105.0, x + repeat + width, y0 + 105.0),
                fill=(225, 233, 242, alpha),
            )
    fog = fog.filter(ImageFilter.GaussianBlur(48))

    snow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    snow_draw = ImageDraw.Draw(snow)
    for x0, y0, speed_y, drift_x, radius, alpha in ambient_flakes():
        x = (x0 + drift_x * t_s + 90.0) % 2100.0 - 90.0
        y = (y0 + speed_y * t_s + 60.0) % 1200.0 - 60.0
        snow_draw.line(
            (x, y, x + drift_x * 0.16, y + radius * 2.8),
            fill=(237, 242, 248, alpha),
            width=max(1, round(radius)),
        )
    return Image.alpha_composite(fog, snow)


def shared_environment(plate: Image.Image, t_s: float, config: dict[str, object]) -> tuple[Image.Image, float]:
    frame = plate.copy()
    frame = ImageEnhance.Contrast(frame).enhance(1.025)
    frame = ImageEnhance.Brightness(frame).enhance(1.035)
    frame = ImageEnhance.Color(frame).enhance(0.96)
    cool = Image.new("RGBA", SIZE, (176, 195, 221, 15))
    frame = Image.alpha_composite(frame.convert("RGBA"), cool)
    frame = Image.alpha_composite(frame, draw_shared_weather(t_s)).convert("RGB")
    return frame, 0.0


@lru_cache(maxsize=2)
def cue_specs(carrier: str) -> tuple[tuple[float, float, float, int], ...]:
    count = 72 if carrier == "target" else 38
    rng = np.random.default_rng(30083047 if carrier == "target" else 30083053)
    x_values = np.clip(rng.normal(0.0, 0.43, count), -1.0, 1.0)
    y_values = np.clip(rng.normal(0.0, 0.39, count), -1.0, 1.0)
    x_values -= float(x_values.mean())
    y_values -= float(y_values.mean())
    sizes = rng.uniform(2.2, 5.4, count)
    alphas = rng.integers(105, 176, count)
    return tuple(
        (float(x), float(y), float(size), int(alpha))
        for x, y, size, alpha in zip(x_values, y_values, sizes, alphas)
    )


def carrier_positions(
    state: float,
    config: dict[str, object],
    carrier: str,
) -> list[tuple[float, float, float, int]]:
    geometry = config["geometry"]
    center_x, neutral_y = (float(value) for value in geometry[f"{carrier}_neutral_center"])
    rise = float(geometry[f"{carrier}_rise_px"])
    neutral_spread_x, neutral_spread_y = (
        float(value) for value in geometry[f"{carrier}_neutral_spread_px"]
    )
    peak_spread_x, peak_spread_y = (
        float(value) for value in geometry[f"{carrier}_peak_spread_px"]
    )
    center_y = neutral_y - rise * state
    spread_x = neutral_spread_x + (peak_spread_x - neutral_spread_x) * state
    spread_y = neutral_spread_y + (peak_spread_y - neutral_spread_y) * state
    return [
        (center_x + nx * spread_x, center_y + ny * spread_y, size, alpha)
        for nx, ny, size, alpha in cue_specs(carrier)
    ]


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


def powder_layer(
    t_s: float,
    config: dict[str, object],
    carrier: str,
) -> tuple[Image.Image, dict[str, float | str | int]]:
    lag_s = float(config["timeline"]["actual_lag_s"])
    phase, progress = phase_state(t_s) if carrier == "target" else actual_state(t_s, lag_s)
    state = motion_state(phase, progress)
    positions = carrier_positions(state, config, carrier)
    crisp = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(crisp)
    if carrier == "target":
        color = (239, 246, 249)
        shadow = (104, 136, 151)
        alpha_scale = 1.0
    else:
        color = (226, 241, 246)
        shadow = (91, 127, 145)
        alpha_scale = 0.9
    for index, (x, y, radius, alpha) in enumerate(positions):
        visible_alpha = round(alpha * alpha_scale)
        arm = radius * (1.25 + 0.12 * (index % 3))
        angle = index * 2.399963 + (0.45 if carrier == "actual" else 0.0)
        dx = math.cos(angle) * arm
        dy = math.sin(angle) * arm * 0.62
        shadow_alpha = round(visible_alpha * 0.58)
        draw.ellipse(
            (
                x - radius * 0.78 + 1.5,
                y - radius * 0.78 + 1.8,
                x + radius * 0.78 + 1.5,
                y + radius * 0.78 + 1.8,
            ),
            fill=(*shadow, shadow_alpha),
        )
        draw.line((x - dx, y - dy, x + dx, y + dy), fill=(*color, visible_alpha), width=2)
        draw.ellipse(
            (x - radius * 0.48, y - radius * 0.48, x + radius * 0.48, y + radius * 0.48),
            fill=(*color, visible_alpha),
        )
    glow = crisp.filter(ImageFilter.GaussianBlur(4 if carrier == "target" else 3))
    combined = Image.alpha_composite(glow, crisp)
    bounds = config["geometry"][f"{carrier}_bounds"]
    centroid_y = sum(position[1] for position in positions) / len(positions)
    return clip_layer(combined, bounds, 36), {
        "phase": phase,
        "progress": progress,
        "state": state,
        "centroid_y": centroid_y,
        "particle_count": len(positions),
        "max_opacity": 175.0 * alpha_scale,
    }


def ring_radius(phase: str, progress: float, minimum: float, maximum: float) -> float:
    state = motion_state(phase, progress)
    return minimum + (maximum - minimum) * state


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
        outline=(191, 225, 238, 220),
        width=8,
    )
    draw.ellipse(
        (center_x - inner_radius, center_y - inner_radius, center_x + inner_radius, center_y + inner_radius),
        outline=(224, 231, 238, 190),
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
    target, target_metrics = powder_layer(t_s, config, "target")
    actual, actual_metrics = powder_layer(t_s, config, "actual")
    rings, ring_metrics = abstract_layer(t_s, config)
    scene = Image.alpha_composite(environment.convert("RGBA"), target)
    scene = Image.alpha_composite(scene, actual).convert("RGB")
    abstract = Image.alpha_composite(environment.convert("RGBA"), rings).convert("RGB")
    return scene, abstract, {"target": target_metrics, "actual": actual_metrics, "rings": ring_metrics}


def review_frame(scene: Image.Image, abstract: Image.Image, t_s: float, metrics: dict[str, object]) -> Image.Image:
    canvas = Image.new("RGB", (3840, 1200), (25, 27, 31))
    canvas.paste(scene, (0, 120))
    canvas.paste(abstract, (1920, 120))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(24)
    target = metrics["target"]
    actual = metrics["actual"]
    draw.text((36, 18), "V-04 H3 INPUT / SNOW / CANDIDATE-V2", font=title_font, fill=(244, 246, 248))
    draw.text(
        (36, 68),
        f"t={t_s:05.2f}s  target={target['phase']}  actual={actual['phase']}  shared fixed camera/snow/fog/audio",
        font=label_font,
        fill=(202, 208, 215),
    )
    draw.text((1390, 68), "SCENE_NATIVE", font=label_font, fill=(192, 228, 240))
    draw.text((3300, 68), "ABSTRACT_PACER", font=label_font, fill=(221, 227, 236))
    return canvas


def cue_difference_mask(config: dict[str, object]) -> np.ndarray:
    mask = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(mask)
    for key in ("target_bounds", "actual_bounds", "abstract_bounds"):
        draw.rectangle(tuple(config["geometry"][key]), fill=255)
    margin = int(config["machine_gates"]["difference_mask_glow_margin_px"])
    mask = mask.filter(ImageFilter.MaxFilter(margin * 2 + 1))
    return np.asarray(mask, dtype=np.uint8) > 0


def make_snow_audio(path: Path, sample_rate: int, duration_s: float) -> None:
    rng = np.random.default_rng(30083059)
    count = round(sample_rate * duration_s)
    time = np.arange(count, dtype=np.float64) / sample_rate
    left_noise = rng.normal(0.0, 1.0, count)
    right_noise = rng.normal(0.0, 1.0, count)
    left = 0.48 * moving_average(left_noise, 340) + 0.36 * moving_average(left_noise, 2600) + 0.16 * moving_average(left_noise, 10500)
    right = 0.46 * moving_average(right_noise, 410) + 0.38 * moving_average(right_noise, 2200) + 0.16 * moving_average(right_noise, 9200)
    air = 0.08 * np.sin(math.tau * 0.031 * time + 0.5) + 0.05 * np.sin(math.tau * 0.057 * time + 2.1)
    stereo = np.column_stack((left + air, right + 0.91 * air))
    stereo /= max(1e-9, float(np.max(np.abs(stereo))))
    write_pcm24(path, stereo * 0.25, sample_rate)


def make_keyframe_sheet(
    frames: list[tuple[float, Image.Image]],
    output: Path,
    grayscale: bool,
    lag_s: float,
) -> None:
    canvas = Image.new("RGB", (1920, 1100), (25, 27, 31))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(22)
    title = "V-04 H3 / SNOW / GRAYSCALE GEOMETRY" if grayscale else "V-04 H3 / SNOW / KEYFRAME REVIEW"
    draw.text((38, 22), title, font=title_font, fill=(245, 247, 249))
    for index, (t_s, frame) in enumerate(frames):
        column = index % 2
        row = index // 2
        x = 35 + column * 950
        y = 82 + row * 330
        thumbnail = frame.resize((900, 281), Image.Resampling.LANCZOS)
        if grayscale:
            thumbnail = thumbnail.convert("L").convert("RGB")
        canvas.paste(thumbnail, (x, y + 28))
        target_phase, _ = phase_state(t_s)
        actual_phase, _ = actual_state(t_s, lag_s)
        draw.text((x, y), f"t={t_s:04.1f}s  target={target_phase}  actual={actual_phase}", font=label_font, fill=(224, 228, 232))
        draw.rectangle((x, y + 28, x + 900, y + 309), outline=(220, 225, 230), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def mirror_state_error(config: dict[str, object], carrier: str) -> float:
    maximum = 0.0
    for p in np.linspace(0.0, 1.0, 101):
        inhale_state = smoothstep(float(p))
        exhale_state = 1.0 - smoothstep(float(1.0 - p))
        inhale = carrier_positions(inhale_state, config, carrier)
        exhale = carrier_positions(exhale_state, config, carrier)
        for left, right in zip(inhale, exhale):
            maximum = max(maximum, math.hypot(left[0] - right[0], left[1] - right[1]))
    return maximum


def geometry_metrics(config: dict[str, object]) -> dict[str, object]:
    lag_s = float(config["timeline"]["actual_lag_s"])
    return {
        "target_vertical_travel_px": float(config["geometry"]["target_rise_px"]),
        "actual_vertical_travel_px": float(config["geometry"]["actual_rise_px"]),
        "target_mirror_state_max_error_px": mirror_state_error(config, "target"),
        "actual_mirror_state_max_error_px": mirror_state_error(config, "actual"),
        "inhale_target_particle_count": len(cue_specs("target")),
        "exhale_target_particle_count": len(cue_specs("target")),
        "inhale_target_max_opacity": 175.0,
        "exhale_target_max_opacity": 175.0,
        "target_at_5s": phase_state(5.0)[0],
        "actual_at_5s": actual_state(5.0, lag_s)[0],
    }


def render_preflight(plate: Image.Image, config: dict[str, object]) -> None:
    output = REPO / ".artifacts-local/V-04/H3/snow-preflight-v2"
    output.mkdir(parents=True, exist_ok=True)
    for t_s in (0.0, 2.5, 4.9, 5.4, 7.5, 9.9):
        environment, _ = shared_environment(plate, t_s, config)
        scene, abstract, metrics = participant_frames(environment, t_s, config)
        review_frame(scene, abstract, t_s, metrics).save(output / f"snow-preflight-{t_s:04.1f}.png")
    print(f"PASS: snow preflight frames written to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    background_selection = json.loads(BACKGROUND_SELECTION.read_text(encoding="utf-8"))
    h2 = json.loads(H2_REVIEW.read_text(encoding="utf-8"))
    require(config["schema_version"] == "2.0", "snow config schema drift")
    require(config["technical_id"] == "snow" and config["preview_id"] == "snow-candidate-v2", "snow identity drift")
    require(config["camera"] == {"mode": "fixed", "horizontal_scroll": False, "camera_displacement_px": 0.0, "source_fit": "cover_center_crop"}, "snow fixed camera drift")
    require(h2["decision"] == "PASS" and h2["results"]["H2"] == "PASS", "H2 has not passed")
    require(background_selection["selection"]["snow"]["candidate_id"] == "R2-C-snow", "snow background selection drift")
    source = REPO / config["source"]["panorama_file"]
    contract = HERE / config["design_contract"]
    mechanism_contract = HERE / config["mechanism_contract"]
    require(source.is_file() and contract.is_file() and mechanism_contract.is_file(), "snow source or contract missing")
    require(sha256(source) == config["source"]["panorama_sha256"], "snow source hash mismatch")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools are missing")
    with Image.open(source) as image:
        source_size = image.size
        plate = prepare_fixed_plate(image)
    if args.preflight:
        render_preflight(plate, config)
        return

    output_root = REPO / config["outputs"]["artifact_root"]
    require(not output_root.exists(), f"snow candidate output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    fps = int(config["timeline"]["fps"])
    frame_count = int(config["timeline"]["frame_count"])
    duration_s = float(config["timeline"]["duration_s"])
    keyframe_indices = {round(float(t) * fps): float(t) for t in config["keyframe_times_s"]}
    keyframes: list[tuple[float, Image.Image]] = []
    difference_mask = cue_difference_mask(config)
    max_outside_difference = 0
    metrics = geometry_metrics(config)

    with tempfile.TemporaryDirectory(prefix="snow-candidate-v2-build-", dir=output_root.parent) as temporary:
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
                require(encoder.wait() == 0, "snow video encoder failed")

        raw_audio = build / "snow-ambient-raw.wav"
        ambient = build / config["outputs"]["ambient_audio"]
        make_snow_audio(raw_audio, int(config["audio"]["sample_rate_hz"]), duration_s)
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
            "schema_version": "2.0",
            "task_id": "V-04",
            "gate_id": "H3_INPUT_PREVIEWS",
            "preview_id": config["preview_id"],
            "technical_id": "snow",
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "design_contract_sha256": sha256(contract),
            "mechanism_contract_sha256": sha256(mechanism_contract),
            "background_selection_sha256": sha256(BACKGROUND_SELECTION),
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
                "camera_mode": "fixed",
                "horizontal_scroll": False,
                "camera_displacement_px": final_displacement,
                "source_fit": "cover_center_crop",
                "background_phase_inputs": config["environment"]["phase_inputs"],
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
                    "height": 1100,
                },
                "grayscale_keyframes": {
                    "file": grayscale_keyframes.relative_to(HERE).as_posix(),
                    "size_bytes": grayscale_keyframes.stat().st_size,
                    "sha256": sha256(grayscale_keyframes),
                    "width": 1920,
                    "height": 1100,
                },
            },
            "asset_status": {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False},
            "gate_status": "MACHINE_VALIDATION_PENDING",
            "next_if_pass": "team-director review with storm-candidate-v2 and heat-candidate-v2",
            "evidence_boundary": "The preview is design evidence only; Unity runtime, formal build and device chain remain unverified.",
        }
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "PASS: rendered snow-candidate-v2; 300 shared fixed-camera frames; "
        f"5-second mirrored inhale/exhale; outside-mask diff={max_outside_difference}"
    )


if __name__ == "__main__":
    main()
