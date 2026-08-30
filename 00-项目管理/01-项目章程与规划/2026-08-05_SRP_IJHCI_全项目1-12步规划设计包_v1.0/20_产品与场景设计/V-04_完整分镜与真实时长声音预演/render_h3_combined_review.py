from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from render_h2_v10 import ffprobe, load_font, media_entry, require, sha256


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3合并评审配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
STORYBOARD_PATH = HERE / "V-04_H3_四天气六节点Unity交接分镜_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3合并评审候选清单_v1.0.json"
REPORT_PATH = HERE / "V-04_H3合并评审机器验收记录_v1.0.json"
EXPECTED_OUTPUT_ROOT = REPO / ".artifacts-local/V-04/H3/combined-review-candidate-v1"
EXPECTED_KEYFRAME_PATH = HERE / "review/H3/V-04-H3-combined-review-keyframes-v1.jpg"
EXPECTED_STORYBOARD_SHEET_PATH = HERE / "review/H3/V-04-H3-six-node-storyboard-v1.jpg"
REVIEW_SIZE = (3840, 1200)


def run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(result.returncode == 0, result.stderr[-4000:] or "command failed")


def nested_value(document: dict[str, object], dotted_path: str) -> object:
    value: object = document
    for part in dotted_path.split("."):
        require(isinstance(value, dict) and part in value, f"missing gate evidence field: {dotted_path}")
        value = value[part]
    return value


def make_slate(path: Path, title: str, subtitle: str, lines: list[str], accent: tuple[int, int, int]) -> None:
    image = Image.new("RGB", REVIEW_SIZE, (24, 27, 31))
    draw = ImageDraw.Draw(image)
    title_font = load_font(76, bold=True)
    subtitle_font = load_font(40, bold=True)
    body_font = load_font(35)
    small_font = load_font(25)
    draw.rectangle((0, 0, REVIEW_SIZE[0], 18), fill=accent)
    draw.text((180, 175), title, font=title_font, fill=(245, 247, 249))
    draw.text((184, 300), subtitle, font=subtitle_font, fill=accent)
    y = 450
    for line in lines:
        draw.text((188, y), line, font=body_font, fill=(211, 216, 222))
        y += 82
    draw.line((188, 910, 3650, 910), fill=(93, 101, 110), width=2)
    draw.text(
        (188, 955),
        "REVIEW-ONLY SLATE / NOT PARTICIPANT OUTPUT / TEMP_REFERENCE_ONLY",
        font=small_font,
        fill=(148, 157, 167),
    )
    image.save(path, format="PNG", optimize=True)


def encode_slate(ffmpeg: Path, image: Path, output: Path, duration_s: float) -> None:
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(image),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-t",
            f"{duration_s:.3f}",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            "-y",
            str(output),
        ]
    )


def assemble(ffmpeg: Path, inputs: list[Path], output: Path) -> None:
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error"]
    for path in inputs:
        command.extend(["-i", str(path)])
    filters: list[str] = []
    concat_inputs: list[str] = []
    for index in range(len(inputs)):
        filters.append(
            f"[{index}:v:0]fps=30,scale=3840:1200:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(f"[{index}:a:0]aresample=48000,asetpts=PTS-STARTPTS[a{index}]")
        concat_inputs.extend([f"[v{index}]", f"[a{index}]"])
    filters.append("".join(concat_inputs) + f"concat=n={len(inputs)}:v=1:a=1[v][a]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-y",
            str(output),
        ]
    )
    run(command)


def extract_frame(ffmpeg: Path, video: Path, time_s: float, output: Path) -> Image.Image:
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{time_s:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-y",
            str(output),
        ]
    )
    with Image.open(output) as image:
        return image.convert("RGB")


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    panel = Image.new("RGB", size, (18, 21, 25))
    thumbnail = image.copy()
    thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
    x = (size[0] - thumbnail.width) // 2
    y = (size[1] - thumbnail.height) // 2
    panel.paste(thumbnail, (x, y))
    return panel


def make_combined_keyframes(
    ffmpeg: Path,
    source_paths: dict[str, Path],
    source_durations: dict[str, float],
    intro: Path,
    outro: Path,
    output: Path,
    temporary: Path,
) -> None:
    panels: list[tuple[str, Image.Image]] = []
    with Image.open(intro) as image:
        panels.append(("INTRO", image.convert("RGB")))
    for section_id in ("storm", "heat", "snow", "fade", "corridor"):
        frame = extract_frame(
            ffmpeg,
            source_paths[section_id],
            source_durations[section_id] * 0.5,
            temporary / f"combined-{section_id}.png",
        )
        panels.append((section_id.upper(), frame))
    with Image.open(outro) as image:
        panels.append(("OUTRO", image.convert("RGB")))

    canvas = Image.new("RGB", (3840, 640), (24, 27, 31))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(34, bold=True)
    label_font = load_font(24, bold=True)
    draw.text((38, 24), "V-04 H3 COMBINED REVIEW / SECTION KEYFRAMES", font=title_font, fill=(244, 246, 248))
    for index, (label, panel) in enumerate(panels):
        x = 36 + index * 542
        y = 105
        thumb = contain(panel, (510, 360))
        canvas.paste(thumb, (x, y))
        draw.rectangle((x, y, x + 510, y + 360), outline=(210, 216, 222), width=2)
        draw.text((x, y + 380), label, font=label_font, fill=(215, 222, 228))
    draw.text(
        (38, 570),
        "REVIEW ORDER ONLY / NOT A RUNTIME WEATHER SEQUENCE",
        font=label_font,
        fill=(151, 161, 171),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def make_storyboard_sheet(
    ffmpeg: Path,
    source_paths: dict[str, Path],
    source_durations: dict[str, float],
    storyboard: dict[str, object],
    style_reference_progress: float,
    output: Path,
    temporary: Path,
) -> None:
    weather_rows = storyboard["weather_storyboards"]
    canvas = Image.new("RGB", (3840, 1600), (24, 27, 31))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(35, bold=True)
    row_font = load_font(27, bold=True)
    node_font = load_font(22, bold=True)
    detail_font = load_font(18)
    draw.text((34, 22), "V-04 H3 / FOUR WEATHER x SIX NODE UNITY HANDOFF", font=title_font, fill=(244, 246, 248))
    draw.text(
        (34, 66),
        "STYLE REFERENCES ONLY - NOT NODE RENDERS - NODE SEMANTICS LIVE IN THE JSON CONTRACT",
        font=detail_font,
        fill=(160, 170, 180),
    )
    cell_width = 620
    cell_height = 350
    x_gap = 12
    row_gap = 20
    start_x = 24
    start_y = 112
    colors = {
        "storm": (118, 167, 190),
        "heat": (218, 163, 102),
        "snow": (183, 204, 219),
        "fade": (148, 193, 164),
    }
    mechanism_labels = {
        "storm": "RAIN CURTAIN GATE",
        "heat": "COOL AIR CORRIDOR",
        "snow": "POWDER SNOW RISE-FALL",
        "fade": "CHROMATIC TIDE RETURN",
    }
    evidence_labels = {
        "ENTRY": "DEMO RECEIPT | TARGET ON | ACTUAL HIDDEN",
        "DEMO_END": "PRE-BOUNDARY TELEMETRY | NO RECEIPT",
        "CLOSED_LOOP_START": "CLOSED_LOOP RECEIPT | NO VISUAL RESET",
        "CLOSED_LOOP_MID": "TELEMETRY CHECKPOINT | NO RECEIPT",
        "CLOSED_LOOP_END": "LAST FRAME | THEN LOCK RECEIPT",
        "TRANSITION_COMPLETE": "NEXT DEMO RECEIPT / FINAL END ACK",
    }
    for row_index, weather in enumerate(weather_rows):
        technical_id = weather["technical_id"]
        nodes = weather["nodes"]
        row_y = start_y + row_index * (cell_height + row_gap)
        draw.text(
            (start_x, row_y),
            f"{technical_id.upper()} / {weather['breath_pattern']} / {mechanism_labels[technical_id]}",
            font=row_font,
            fill=colors[technical_id],
        )
        for node_index, node in enumerate(nodes):
            x = start_x + node_index * (cell_width + x_gap)
            y = row_y + 42
            if node_index < 5:
                source_id = technical_id
                progress = style_reference_progress
            else:
                source_id = "corridor"
                progress = float(node["reference_sample"]["progress"])
            frame = extract_frame(
                ffmpeg,
                source_paths[source_id],
                source_durations[source_id] * progress,
                temporary / f"storyboard-{technical_id}-{node['node_id']}.png",
            )
            thumb = ImageEnhance.Brightness(fit(frame, (600, 188))).enhance(0.72)
            canvas.paste(thumb, (x + 10, y + 42))
            draw.rectangle((x, y, x + cell_width, y + 308), outline=(77, 85, 94), width=2)
            draw.rectangle((x, y, x + cell_width, y + 34), fill=colors[technical_id])
            draw.text((x + 10, y + 5), node["node_id"], font=node_font, fill=(20, 24, 28))
            draw.rectangle((x + 10, y + 42, x + 610, y + 68), fill=(22, 25, 29))
            draw.text((x + 18, y + 45), "STYLE REFERENCE ONLY / NOT RUNTIME CAPTURE", font=detail_font, fill=(236, 239, 242))
            draw.text(
                (x + 10, y + 238),
                f"t_ref={node['module_time_s']:.0f}s  visual_segment={node['visual_segment']}",
                font=detail_font,
                fill=(220, 224, 229),
            )
            draw.text((x + 10, y + 271), evidence_labels[node["node_id"]], font=detail_font, fill=(166, 176, 186))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)


def image_entry(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
    return {
        "file": path.relative_to(HERE).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "width": width,
        "height": height,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    storyboard = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    require(config["candidate_id"] == "h3-combined-review-candidate-v1", "candidate identity drift")
    require(config["review_order_is_runtime_sequence"] is False, "review order must not bind runtime sequence")
    require(storyboard["document_id"] == "V04_H3_SIX_NODE_UNITY_HANDOFF_1_0", "storyboard identity drift")
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    ffprobe_path = Path(lock["ffmpeg"]["ffprobe_executable"])
    require(ffmpeg.is_file() and ffprobe_path.is_file(), "locked FFmpeg tools are missing")

    source_paths: dict[str, Path] = {}
    source_durations: dict[str, float] = {}
    source_manifest_entries: list[dict[str, object]] = []
    for section in config["sections"]:
        section_id = section["section_id"]
        source = REPO / section["source_file"]
        source_manifest = HERE / section["source_manifest"]
        gate_evidence = section["gate_evidence"]
        gate_evidence_path = HERE / gate_evidence["file"]
        require(source.is_file() and sha256(source) == section["source_sha256"], f"{section_id} media drift")
        require(source_manifest.is_file(), f"{section_id} source manifest missing")
        require(gate_evidence_path.resolve().parent == HERE.resolve(), f"{section_id} unsafe gate evidence path")
        require(gate_evidence_path.is_file(), f"{section_id} gate evidence missing")
        gate_document = json.loads(gate_evidence_path.read_text(encoding="utf-8"))
        for dotted_path, expected in gate_evidence["assertions"].items():
            require(nested_value(gate_document, dotted_path) == expected, f"{section_id} gate assertion failed: {dotted_path}")
        require(
            nested_value(gate_document, gate_evidence["media_sha256_path"]) == section["source_sha256"],
            f"{section_id} gate media hash drift",
        )
        source_paths[section_id] = source
        source_durations[section_id] = float(section["duration_s"])
        source_manifest_entries.append(
            {
                "section_id": section_id,
                "label": section["label"],
                "source_gate": section["source_gate"],
                "source_file": section["source_file"],
                "source_sha256": section["source_sha256"],
                "source_manifest": section["source_manifest"],
                "source_manifest_sha256": sha256(source_manifest),
                "gate_evidence_file": gate_evidence["file"],
                "gate_evidence_sha256": sha256(gate_evidence_path),
                "gate_assertions": gate_evidence["assertions"],
                "gate_media_sha256_path": gate_evidence["media_sha256_path"],
                "duration_s": section["duration_s"],
            }
        )

    output_root = REPO / config["outputs"]["artifact_root"]
    keyframe_output = HERE / config["outputs"]["combined_keyframes"]
    storyboard_output = HERE / config["outputs"]["storyboard_sheet"]
    require(output_root.resolve() == EXPECTED_OUTPUT_ROOT.resolve(), "unsafe candidate output path")
    require(keyframe_output.resolve() == EXPECTED_KEYFRAME_PATH.resolve(), "unsafe keyframe output path")
    require(storyboard_output.resolve() == EXPECTED_STORYBOARD_SHEET_PATH.resolve(), "unsafe storyboard output path")
    require(MANIFEST_PATH.resolve().parent == HERE.resolve(), "unsafe manifest output path")
    require(REPORT_PATH.resolve().parent == HERE.resolve(), "unsafe report output path")
    require(config["outputs"]["combined_video"] == "V-04-H3-combined-review-candidate-v1.mp4", "combined video output drift")
    if args.replace_generated:
        if output_root.exists():
            shutil.rmtree(output_root)
        for generated in (keyframe_output, storyboard_output, MANIFEST_PATH, REPORT_PATH):
            generated.unlink(missing_ok=True)
    require(not output_root.exists(), f"combined candidate output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix="h3-combined-review-build-", dir=output_root.parent))
    try:
        intro_png = build / "intro.png"
        outro_png = build / "outro.png"
        intro_mp4 = build / "intro.mp4"
        outro_mp4 = build / "outro.mp4"
        make_slate(
            intro_png,
            "V-04 H3 COMBINED DESIGN REVIEW",
            "FOUR WEATHER MECHANISMS + ONE SHARED TRANSITION",
            [
                "SCENE_NATIVE  |  ABSTRACT_PACER",
                "REVIEW ORDER IS NOT THE RUNTIME WEATHER SEQUENCE",
                "SIX-NODE UNITY HANDOFF IS REVIEWED SEPARATELY",
            ],
            (112, 181, 195),
        )
        make_slate(
            outro_png,
            "TEAM DIRECTOR H3 CHECK",
            "CONFIRM THE DESIGN PACKAGE, NOT A RUNTIME BUILD",
            [
                "1  FOUR CORE MECHANISMS ARE READABLE",
                "2  TARGET AND ACTUAL REMAIN DISTINGUISHABLE",
                "3  ONLY TARGET/ACTUAL ORGANIZATION DIFFERS BY CONDITION",
                "4  THE NEUTRAL CORRIDOR DOES NOT BIND A WEATHER ORDER",
                "5  THE 4 x 6 NODE HANDOFF CAN START UNITY GRAYBOX WORK",
            ],
            (187, 164, 111),
        )
        encode_slate(ffmpeg, intro_png, intro_mp4, float(config["slates"]["intro_duration_s"]))
        encode_slate(ffmpeg, outro_png, outro_mp4, float(config["slates"]["outro_duration_s"]))

        combined_video = build / config["outputs"]["combined_video"]
        ordered_inputs = [intro_mp4]
        ordered_inputs.extend(source_paths[section["section_id"]] for section in config["sections"])
        ordered_inputs.append(outro_mp4)
        assemble(ffmpeg, ordered_inputs, combined_video)

        keyframe_temp = build / "combined-keyframes.jpg"
        storyboard_temp = build / "storyboard-sheet.jpg"
        make_combined_keyframes(
            ffmpeg,
            source_paths,
            source_durations,
            intro_png,
            outro_png,
            keyframe_temp,
            build,
        )
        make_storyboard_sheet(
            ffmpeg,
            source_paths,
            source_durations,
            storyboard,
            float(config["weather_style_reference_progress"]),
            storyboard_temp,
            build,
        )

        keyframe_output.parent.mkdir(parents=True, exist_ok=True)
        storyboard_output.parent.mkdir(parents=True, exist_ok=True)
        os.replace(keyframe_temp, keyframe_output)
        os.replace(storyboard_temp, storyboard_output)

        timeline: list[dict[str, object]] = []
        cursor = float(config["slates"]["intro_duration_s"])
        for section in config["sections"]:
            duration = float(section["duration_s"])
            timeline.append(
                {
                    "section_id": section["section_id"],
                    "start_s": cursor,
                    "end_s": cursor + duration,
                    "duration_s": duration,
                }
            )
            cursor += duration
        expected_duration = cursor + float(config["slates"]["outro_duration_s"])
        require(expected_duration == float(config["render"]["expected_duration_s"]), "expected duration drift")
        combined_probe = ffprobe(ffprobe_path, combined_video)
        manifest = {
            "schema_version": "1.0",
            "task_id": "V-04",
            "gate_id": "H3_COMBINED_REVIEW",
            "candidate_id": config["candidate_id"],
            "generated_at": config["render_requested_at"],
            "config_sha256": sha256(CONFIG_PATH),
            "design_contract_sha256": sha256(HERE / config["design_contract"]),
            "storyboard_json_sha256": sha256(STORYBOARD_PATH),
            "storyboard_markdown_sha256": sha256(HERE / config["storyboard_markdown"]),
            "unity_handoff_checklist_sha256": sha256(HERE / config["unity_handoff_checklist"]),
            "review_order_is_runtime_sequence": False,
            "source_sections": source_manifest_entries,
            "timeline": {
                "intro": {"start_s": 0.0, "end_s": float(config["slates"]["intro_duration_s"])},
                "sections": timeline,
                "outro": {"start_s": cursor, "end_s": expected_duration},
                "duration_s": expected_duration,
            },
            "storyboard": {
                "weather_count": len(storyboard["weather_storyboards"]),
                "nodes_per_weather": [len(weather["nodes"]) for weather in storyboard["weather_storyboards"]],
                "total_node_count": sum(len(weather["nodes"]) for weather in storyboard["weather_storyboards"]),
                "reference_frames_are_runtime_captures": False,
                "reference_frames_are_style_only": True,
            },
            "outputs": {
                "combined_video": media_entry(combined_video, combined_probe),
                "combined_keyframes": image_entry(keyframe_output),
                "storyboard_sheet": image_entry(storyboard_output),
            },
            "asset_status": config["asset_status"],
            "gate_status": "MACHINE_VALIDATION_PENDING",
            "next_if_pass": "INDEPENDENT_AGENT_REVIEW_THEN_TEAM_DIRECTOR_H3_CONFIRMATION",
            "evidence_boundary": "Design review evidence only; Unity runtime, build, licensed production assets and live device chain remain unverified.",
        }
        for path in build.glob("*.png"):
            path.unlink(missing_ok=True)
        for path in (intro_mp4, outro_mp4):
            path.unlink(missing_ok=True)
        os.replace(build, output_root)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        if build.exists():
            shutil.rmtree(build)

    print("PASS: rendered 62s H3 combined review and four-weather six-node reference sheet")


if __name__ == "__main__":
    main()
