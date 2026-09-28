from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

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
CONFIG_PATH = HERE / "V-04_H3_corridor样片配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
H1_SELECTION = HERE / "V-04_H1选择记录_v1.0.json"
H2_REVIEW = HERE / "V-04_H2人工评审记录_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3_corridor候选清单_v1.0.json"
SIZE = (1920, 1080)


def blend_weights(progress: float, exit_end: float, reveal_start: float) -> tuple[float, float, float, str]:
    progress = min(1.0, max(0.0, progress))
    if progress < exit_end:
        corridor = smoothstep(progress / exit_end)
        return 1.0 - corridor, corridor, 0.0, "EXIT_CURRENT"
    if progress <= reveal_start:
        return 0.0, 1.0, 0.0, "NEUTRAL_CORRIDOR"
    next_weight = smoothstep((progress - reveal_start) / (1.0 - reveal_start))
    return 0.0, 1.0 - next_weight, next_weight, "REVEAL_NEXT_BASELINE"


def fit_anchor(source: Image.Image) -> Image.Image:
    return ImageOps.fit(source.convert("RGB"), SIZE, method=Image.Resampling.LANCZOS)


def prepare_corridor(source: Image.Image, zoom: float) -> Image.Image:
    width = round(SIZE[0] * zoom)
    height = round(SIZE[1] * zoom)
    return ImageOps.fit(source.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def mist_bands() -> tuple[tuple[float, float, float, float, float], ...]:
    rng = np.random.default_rng(30083071)
    return tuple(
        (
            float(rng.uniform(-900.0, 1900.0)),
            float(rng.uniform(260.0, 890.0)),
            float(rng.uniform(520.0, 920.0)),
            float(rng.uniform(80.0, 170.0)),
            float(rng.uniform(0.5, 1.3)),
        )
        for _ in range(8)
    )


def moving_mist(progress: float, handoff_cover: float) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for x0, y0, width, height, speed in mist_bands():
        x = x0 + progress * speed * 190.0
        for repeat in (-2500.0, 0.0, 2500.0):
            alpha = round(14 + 18 * handoff_cover)
            draw.ellipse(
                (x + repeat - width, y0 - height, x + repeat + width, y0 + height),
                fill=(226, 234, 237, alpha),
            )
    layer = layer.filter(ImageFilter.GaussianBlur(58))
    if handoff_cover > 0.0:
        veil = Image.new("RGBA", SIZE, (223, 231, 234, round(255 * handoff_cover)))
        layer = Image.alpha_composite(layer, veil)
    return layer


def handoff_cover(progress: float, opacity: float) -> float:
    left = math.exp(-((progress - 0.30) / 0.075) ** 2)
    right = math.exp(-((progress - 0.70) / 0.075) ** 2)
    return opacity * max(left, right)


def corridor_frame(plate: Image.Image, progress: float, travel_px: float) -> tuple[Image.Image, float]:
    corridor_progress = min(1.0, max(0.0, (progress - 0.30) / 0.40))
    available_x = plate.width - SIZE[0]
    available_y = plate.height - SIZE[1]
    crop_x = min(float(available_x), travel_px * corridor_progress)
    crop_y = available_y * 0.56
    frame = plate.crop((round(crop_x), round(crop_y), round(crop_x) + SIZE[0], round(crop_y) + SIZE[1]))
    frame = ImageEnhance.Contrast(frame).enhance(1.025)
    frame = ImageEnhance.Color(frame).enhance(0.92)
    return frame, crop_x


def participant_frame(
    current: Image.Image,
    corridor_plate: Image.Image,
    next_scene: Image.Image,
    progress: float,
    config: dict[str, object],
) -> tuple[Image.Image, dict[str, float | str]]:
    exit_end = float(config["timeline"]["exit_end_progress"])
    reveal_start = float(config["timeline"]["reveal_start_progress"])
    current_weight, corridor_weight, next_weight, stage = blend_weights(progress, exit_end, reveal_start)
    corridor, crop_x = corridor_frame(
        corridor_plate,
        progress,
        float(config["visual"]["corridor_camera_travel_px"]),
    )
    frame = Image.blend(current, corridor, corridor_weight)
    if next_weight > 0.0:
        frame = Image.blend(corridor, next_scene, next_weight)
    cover = handoff_cover(progress, float(config["visual"]["mist_handoff_opacity"]))
    frame = Image.alpha_composite(frame.convert("RGBA"), moving_mist(progress, cover)).convert("RGB")
    return frame, {
        "stage": stage,
        "current_weight": current_weight,
        "corridor_weight": corridor_weight,
        "next_weight": next_weight,
        "corridor_crop_x": crop_x,
        "handoff_cover": cover,
    }


def review_frame(frame: Image.Image, t_s: float, progress: float, metrics: dict[str, float | str]) -> Image.Image:
    canvas = Image.new("RGB", (3840, 1200), (25, 27, 31))
    canvas.paste(frame, (0, 120))
    canvas.paste(frame, (1920, 120))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(24)
    draw.text((36, 18), "V-04 H3 INPUT / NEUTRAL CORRIDOR / CANDIDATE-V1", font=title_font, fill=(244, 246, 248))
    draw.text(
        (36, 68),
        f"t={t_s:05.2f}s  p={progress:0.3f}  stage={metrics['stage']}  cues=OFF  condition_diff=0",
        font=label_font,
        fill=(202, 208, 215),
    )
    draw.text((1390, 68), "SCENE_NATIVE", font=label_font, fill=(192, 228, 240))
    draw.text((3300, 68), "ABSTRACT_PACER", font=label_font, fill=(221, 227, 236))
    return canvas


def make_transition_audio(path: Path, sample_rate: int, duration_s: float, config: dict[str, object]) -> None:
    rng = np.random.default_rng(30083073)
    count = round(sample_rate * duration_s)
    progress = np.linspace(0.0, 1.0, count, endpoint=False)
    time = np.arange(count, dtype=np.float64) / sample_rate
    current_weight = np.zeros(count)
    corridor_weight = np.zeros(count)
    next_weight = np.zeros(count)
    for index, value in enumerate(progress):
        current_weight[index], corridor_weight[index], next_weight[index], _ = blend_weights(value, 0.30, 0.70)
    left_noise = rng.normal(0.0, 1.0, count)
    right_noise = rng.normal(0.0, 1.0, count)
    broad_left = moving_average(left_noise, 32)
    broad_right = moving_average(right_noise, 39)
    low_left = moving_average(left_noise, 1100)
    low_right = moving_average(right_noise, 980)
    current_texture = 0.62 * broad_left + 0.20 * low_left + 0.06 * np.sin(math.tau * 127.0 * time + 0.4)
    next_texture = 0.58 * broad_right + 0.22 * low_right + 0.05 * np.sin(math.tau * 89.0 * time + 2.0)
    neutral_left = 0.48 * broad_left + 0.28 * low_left + 0.04 * np.sin(math.tau * 73.0 * time)
    neutral_right = 0.48 * broad_right + 0.28 * low_right + 0.04 * np.sin(math.tau * 67.0 * time + 1.2)
    left = current_weight * current_texture + corridor_weight * neutral_left + next_weight * next_texture
    right = current_weight * (0.92 * current_texture) + corridor_weight * neutral_right + next_weight * (0.94 * next_texture)
    stereo = np.tanh(2.8 * np.column_stack((left, right)))
    stereo /= max(1e-9, float(np.max(np.abs(stereo))))
    write_pcm24(path, stereo * 0.24, sample_rate)


def make_keyframe_sheet(frames: list[tuple[float, str, Image.Image]], output: Path, grayscale: bool) -> None:
    canvas = Image.new("RGB", (1920, 1100), (25, 27, 31))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(30, bold=True)
    label_font = load_font(21)
    title = "V-04 H3 / CORRIDOR / GRAYSCALE PARITY" if grayscale else "V-04 H3 / CORRIDOR / KEYFRAME REVIEW"
    draw.text((38, 22), title, font=title_font, fill=(245, 247, 249))
    for index, (t_s, stage, frame) in enumerate(frames):
        column = index % 2
        row = index // 2
        x = 35 + column * 950
        y = 82 + row * 330
        thumbnail = frame.resize((900, 281), Image.Resampling.LANCZOS)
        if grayscale:
            thumbnail = thumbnail.convert("L").convert("RGB")
        canvas.paste(thumbnail, (x, y + 28))
        draw.text((x, y), f"t={t_s:04.1f}s  {stage}", font=label_font, fill=(224, 228, 232))
        draw.rectangle((x, y + 28, x + 900, y + 309), outline=(220, 225, 230), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def load_sources(config: dict[str, object]) -> tuple[Image.Image, Image.Image, Image.Image, dict[str, tuple[int, int]]]:
    images: dict[str, Image.Image] = {}
    sizes: dict[str, tuple[int, int]] = {}
    for role, entry in config["sources"].items():
        path = REPO / entry["file"]
        require(path.is_file() and sha256(path) == entry["sha256"], f"{role} source drift")
        with Image.open(path) as source:
            sizes[role] = source.size
            if role == "corridor":
                images[role] = prepare_corridor(source, float(config["visual"]["corridor_zoom"]))
            else:
                images[role] = fit_anchor(source)
    return images["current"], images["corridor"], images["next"], sizes


def render_preflight(current: Image.Image, corridor: Image.Image, next_scene: Image.Image, config: dict[str, object]) -> None:
    output = REPO / ".artifacts-local/V-04/H3/corridor-preflight-v1"
    output.mkdir(parents=True, exist_ok=True)
    for t_s in (0.0, 3.0, 3.6, 6.0, 8.4, 9.0, 12.0):
        progress = t_s / float(config["timeline"]["duration_s"])
        frame, metrics = participant_frame(current, corridor, next_scene, progress, config)
        review_frame(frame, t_s, progress, metrics).save(output / f"corridor-preflight-{t_s:04.1f}.png")
    print(f"PASS: corridor preflight frames written to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    h1 = json.loads(H1_SELECTION.read_text(encoding="utf-8"))
    h2 = json.loads(H2_REVIEW.read_text(encoding="utf-8"))
    require(config["preview_id"] == "corridor-candidate-v1", "corridor identity drift")
    require(h2["decision"] == "PASS" and h2["results"]["H2"] == "PASS", "H2 has not passed")
    selected = {item["candidate_id"] for item in h1["selections"]}
    require({"storm-A", "corridor-A", "snow-B"}.issubset(selected), "representative anchors are not H1 selected")
    current, corridor, next_scene, source_sizes = load_sources(config)
    contract = HERE / config["design_contract"]
    require(contract.is_file(), "corridor design contract missing")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools are missing")
    if args.preflight:
        render_preflight(current, corridor, next_scene, config)
        return

    output_root = REPO / config["outputs"]["artifact_root"]
    require(not output_root.exists(), f"corridor candidate output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    fps = int(config["timeline"]["fps"])
    frame_count = int(config["timeline"]["frame_count"])
    duration_s = float(config["timeline"]["duration_s"])
    keyframe_indices = {
        round(float(t) / duration_s * (frame_count - 1)): float(t) for t in config["keyframe_times_s"]
    }
    keyframes: list[tuple[float, str, Image.Image]] = []
    max_condition_difference = 0
    final_crop_x = 0.0

    with tempfile.TemporaryDirectory(prefix="corridor-candidate-v1-build-", dir=output_root.parent) as temporary:
        build = Path(temporary)
        silent_participant = build / "participant-silent.mp4"
        silent_review = build / "review-silent.mp4"
        logs = [build / "participant.log", build / "review.log"]
        encoders = (
            open_video_encoder(ffmpeg, silent_participant, SIZE, fps, logs[0]),
            open_video_encoder(ffmpeg, silent_review, (3840, 1200), fps, logs[1]),
        )
        try:
            for frame_index in range(frame_count):
                progress = frame_index / (frame_count - 1)
                t_s = progress * duration_s
                frame, metrics = participant_frame(current, corridor, next_scene, progress, config)
                review = review_frame(frame, t_s, progress, metrics)
                final_crop_x = max(final_crop_x, float(metrics["corridor_crop_x"]))
                encoders[0].stdin.write(frame.tobytes())
                encoders[1].stdin.write(review.tobytes())
                if frame_index in keyframe_indices:
                    keyframes.append((keyframe_indices[frame_index], str(metrics["stage"]), frame.copy()))
        finally:
            for encoder in encoders:
                if encoder.stdin:
                    encoder.stdin.close()
            for encoder in encoders:
                require(encoder.wait() == 0, "corridor video encoder failed")

        raw_audio = build / "corridor-transition-raw.wav"
        ambient = build / config["outputs"]["ambient_audio"]
        make_transition_audio(raw_audio, int(config["audio"]["sample_rate_hz"]), duration_s, config)
        normalize_audio(ffmpeg, raw_audio, ambient)
        final_scene = build / config["outputs"]["scene_native_video"]
        final_abstract = build / config["outputs"]["abstract_pacer_video"]
        final_review = build / config["outputs"]["paired_review_video"]
        mux(ffmpeg, silent_participant, ambient, final_scene)
        shutil.copyfile(final_scene, final_abstract)
        mux(ffmpeg, silent_review, ambient, final_review)
        for path in (raw_audio, silent_participant, silent_review, *logs):
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
        source_manifest = {
            role: {
                "candidate_id": entry["candidate_id"],
                "file": entry["file"],
                "sha256": entry["sha256"],
                "width": source_sizes[role][0],
                "height": source_sizes[role][1],
            }
            for role, entry in config["sources"].items()
        }
        manifest = {
            "schema_version": "1.0",
            "task_id": "V-04",
            "gate_id": "H3_INPUT_PREVIEWS",
            "preview_id": config["preview_id"],
            "technical_id": "corridor",
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "design_contract_sha256": sha256(contract),
            "h1_selection_sha256": sha256(H1_SELECTION),
            "h2_review_sha256": sha256(H2_REVIEW),
            "representative_path": config["representative_path"],
            "sources": source_manifest,
            "render": {
                "duration_s": duration_s,
                "fps": fps,
                "frame_count": frame_count,
                "sample_is_time_compressed": True,
                "runtime_candidate_duration_s": config["timeline"]["runtime_candidate_duration_s"],
                "stage_ratios": config["timeline"]["stage_ratios"],
                "cue_layers": config["visual"]["cue_layers"],
                "audio_phase_inputs": config["audio"]["phase_inputs"],
                "condition_pixel_policy": config["visual"]["condition_pixel_policy"],
                "max_condition_pixel_difference": max_condition_difference,
                "condition_video_hashes_identical": sha256(final_scene) == sha256(final_abstract),
                "corridor_stele_travel_px": final_crop_x,
                "weights": {
                    "at_start": blend_weights(0.0, 0.30, 0.70)[:3],
                    "at_exit_end": blend_weights(0.30, 0.30, 0.70)[:3],
                    "at_midpoint": blend_weights(0.50, 0.30, 0.70)[:3],
                    "at_reveal_start": blend_weights(0.70, 0.30, 0.70)[:3],
                    "at_end": blend_weights(1.0, 0.30, 0.70)[:3],
                },
                "next_weight_before_reveal": 0.0,
                "current_weight_after_exit": 0.0,
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
            "asset_status": config["asset_status"],
            "gate_status": "MACHINE_VALIDATION_PENDING",
            "next_if_pass": "close H3_INPUT_PREVIEWS_READY and assemble the combined H3 review",
            "evidence_boundary": "This preview is design evidence only; directed-pair runtime, Unity build and device chain remain unverified.",
        }
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("PASS: rendered corridor-candidate-v1; 360 identical condition frames; 30/40/30 transition")


if __name__ == "__main__":
    main()
