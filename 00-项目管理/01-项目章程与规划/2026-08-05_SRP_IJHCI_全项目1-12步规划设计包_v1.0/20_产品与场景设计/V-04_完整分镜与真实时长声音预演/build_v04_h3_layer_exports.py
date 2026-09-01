"""Build the V-04 H3 fixed-camera transparent background package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re

import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "AGENTS.md").is_file())
RECIPE_PATH = HERE / "V-04_H3_透明分层配方_v1.0.json"
ALLOWED_ROOT = ROOT / ".artifacts-local/V-04/H3/layerable-background-rebuild"
DEFAULT_OUTPUT = ALLOWED_ROOT / "layer-export-candidate-v1"
FFMPEG = ROOT / ".tools/ffmpeg/9.0.1/ffmpeg-9.0.1-essentials_build/bin/ffmpeg.exe"
WEATHER_ORDER = ("fade", "heat", "storm", "snow")
PREVIEW_SIZE = (1920, 1080)
STACK_SIZE = (1280, 720)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False, compress_level=9)


def resolve_output(raw: str | None) -> Path:
    output = DEFAULT_OUTPUT if raw is None else (ROOT / raw)
    output = output.resolve()
    allowed = ALLOWED_ROOT.resolve()
    try:
        output.relative_to(allowed)
    except ValueError as exc:
        raise ValueError("output must stay under the H3 layerable-background artifact root") from exc
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output already exists and is not empty: {output}")
    return output


def interpolate_boundaries(boundaries: list, width: int, height: int) -> np.ndarray:
    sample_x = np.linspace(0.0, 1.0, width)
    rows: list[np.ndarray] = []
    prior = np.full(width, -1, dtype=np.int32)
    for points in boundaries:
        point_array = np.asarray(points, dtype=np.float64)
        row = np.rint(np.interp(sample_x, point_array[:, 0], point_array[:, 1]) * (height - 1)).astype(np.int32)
        row = np.maximum(row, prior + 2)
        row = np.minimum(row, height - 2)
        rows.append(row)
        prior = row
    return np.stack(rows)


def ownership_map(boundaries: np.ndarray, width: int, height: int) -> np.ndarray:
    y = np.arange(height, dtype=np.int32)[:, None]
    owner = np.zeros((height, width), dtype=np.uint8)
    for boundary in boundaries:
        owner += y >= boundary[None, :]
    return owner


def build_layer(master: np.ndarray, boundaries: np.ndarray, index: int, bleed: int) -> tuple[Image.Image, Image.Image]:
    height, width, _ = master.shape
    y = np.arange(height, dtype=np.int32)[:, None]
    x = np.broadcast_to(np.arange(width, dtype=np.int32)[None, :], (height, width))
    start = np.zeros(width, dtype=np.int32) if index == 0 else boundaries[index - 1]
    end = np.full(width, height, dtype=np.int32) if index == 6 else boundaries[index]

    owner = (y >= start[None, :]) & (y < end[None, :])
    if index == 0:
        alpha = np.ones((height, width), dtype=bool)
    elif index == 6:
        alpha = owner
    else:
        alpha = (y >= start[None, :]) & (y < np.minimum(end + bleed, height)[None, :])

    sample_y = np.maximum(y, start[None, :])
    sample_y = np.minimum(sample_y, np.maximum(end - 1, start)[None, :]).astype(np.int32)
    rgb = master[sample_y, x].copy()
    rgb[~alpha] = 0
    rgba = np.dstack((rgb, alpha.astype(np.uint8) * 255))
    owner_image = Image.fromarray(owner.astype(np.uint8) * 255, mode="L")
    return Image.fromarray(rgba, mode="RGBA"), owner_image


def checkerboard(size: tuple[int, int], cell: int = 32) -> Image.Image:
    width, height = size
    yy, xx = np.indices((height, width))
    values = np.where(((xx // cell) + (yy // cell)) % 2 == 0, 210, 165).astype(np.uint8)
    rgb = np.dstack((values, values, values))
    return Image.fromarray(rgb, mode="RGB").convert("RGBA")


def labeled(image: Image.Image, text: str) -> Image.Image:
    result = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(result)
    box = draw.textbbox((0, 0), text)
    width = box[2] - box[0] + 20
    height = box[3] - box[1] + 16
    draw.rectangle((8, 8, 8 + width, 8 + height), fill=(0, 0, 0, 190))
    draw.text((18, 16), text, fill=(255, 255, 255, 255))
    return result


def contact_sheet(images: list[tuple[str, Image.Image]], cell_size: tuple[int, int]) -> Image.Image:
    columns = 4
    rows = 2
    sheet = Image.new("RGBA", (columns * cell_size[0], rows * cell_size[1]), (28, 28, 28, 255))
    for index, (name, image) in enumerate(images):
        cell = labeled(image.convert("RGBA").resize(cell_size, Image.Resampling.LANCZOS), name)
        sheet.alpha_composite(cell, ((index % columns) * cell_size[0], (index // columns) * cell_size[1]))
    return sheet


def safe_area_preview(master: Image.Image, safe_areas: dict) -> Image.Image:
    preview = master.resize(PREVIEW_SIZE, Image.Resampling.LANCZOS).convert("RGBA")
    draw = ImageDraw.Draw(preview)
    colors = {"actual": (0, 230, 255, 255), "target": (70, 235, 100, 255)}
    for name in ("actual", "target"):
        area = safe_areas[name]
        left = round(area["x_min"] * PREVIEW_SIZE[0])
        right = round(area["x_max"] * PREVIEW_SIZE[0])
        top = round((1.0 - area["y_max"]) * PREVIEW_SIZE[1])
        bottom = round((1.0 - area["y_min"]) * PREVIEW_SIZE[1])
        draw.rectangle((left, top, right, bottom), outline=colors[name], width=5)
        draw.text((left + 8, top + 8), name, fill=colors[name])
    return preview


def write_stack_frames(
    weather: str,
    layers: list[tuple[str, Image.Image]],
    output: Path,
) -> list[Path]:
    base = checkerboard((3840, 2160), 48)
    frames: list[Path] = []
    stage = base.copy()
    frame_path = output / f"{weather}-stack-00.png"
    save_png(labeled(stage.resize(STACK_SIZE, Image.Resampling.LANCZOS), f"{weather}: empty canvas"), frame_path)
    frames.append(frame_path)
    for index, (name, layer) in enumerate(layers, start=1):
        stage = Image.alpha_composite(stage, layer)
        frame_path = output / f"{weather}-stack-{index:02d}.png"
        preview = labeled(stage.resize(STACK_SIZE, Image.Resampling.LANCZOS), f"{weather}: + {name}")
        save_png(preview, frame_path)
        frames.append(frame_path)
    return frames


def write_review_video(frames: list[Path], package_root: Path) -> Path:
    if not FFMPEG.is_file():
        raise FileNotFoundError(f"locked FFmpeg is missing: {FFMPEG}")
    concat_path = package_root / "source/review_concat.txt"
    concat_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for frame in frames:
        escaped = frame.relative_to(concat_path.parent).as_posix().replace("'", "'\\''")
        lines.extend((f"file '{escaped}'", "duration 0.75"))
    lines.append(f"file '{frames[-1].as_posix()}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    video = package_root / "preview/H3-layer-stack-review.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_path), "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-movflags", "+faststart", str(video),
    ]
    result = subprocess.run(command, cwd=concat_path.parent, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg review render failed: {result.stderr.strip()}")
    return video


def manifest_row(weather: str, layer: dict, source: dict, output_path: Path, candidate_id: str) -> dict[str, str]:
    return {
        "asset_id": f"V04-H3-{weather.upper()}-{layer['name'].upper()}",
        "category": "IMAGE",
        "scene": weather,
        "layer_role": layer["name"],
        "author_source": "OpenAI image generation; team director selection; Codex deterministic layer extraction",
        "license": "PENDING_G02_CLEARANCE",
        "ledger_group": "srp-ai-generated-v04-h3-pending",
        "status": "PENDING_G02_CLEARANCE",
        "formal_use_allowed": "false",
        "replacement_plan": "U-03 and G-02 must clear this exact hash or replace the asset before formal build",
        "owner": "Unity visual lead",
        "deadline": "U-03_ASSET_IMPORT_GATE",
        "hash_or_version": sha256_file(output_path),
        "unity_import_plan": f"parent={layer['unity_parent']}; depth_index={layer['depth_index']}; fixed_camera; no_parallax",
        "source_or_internal_path": source["source_path"],
        "obtained_or_generated_on": "2026-08-31+08:00",
        "evidence_path": "V-04_H3_透明分层交付合同_v1.0.md",
        "tool": "OpenAI built-in image generation; Python 3.14.4; Pillow 12.2.0; NumPy 2.4.6",
        "model_version_if_exposed": "NOT_EXPOSED",
        "prompt_version": "V-04_H3_R2大景深AAA背景生图提示词_v1.0; fade source record v1.0",
        "reference_ids": f"{weather}:{source['selected_direction']}",
        "source_sha256": source["source_sha256"],
        "final_sha256": sha256_file(output_path),
        "human_modifier": "Codex layer extraction; pending team director review",
        "asset_version": candidate_id,
        "runtime_path": "PENDING_UNITY_IMPORT",
    }


def build_weather(recipe: dict, weather: str, package_root: Path, candidate_id: str) -> tuple[list[dict[str, str]], list[Path], dict]:
    source = recipe["weathers"][weather]
    source_path = ROOT / source["source_path"]
    if not source_path.is_file():
        raise FileNotFoundError(f"missing selected base image: {source_path}")
    if sha256_file(source_path) != source["source_sha256"]:
        raise ValueError(f"source hash drift: {weather}")
    with Image.open(source_path) as image:
        if list(image.size) != source["source_size"]:
            raise ValueError(f"source dimensions drift: {weather}")
        master = image.convert("RGB").resize(
            (recipe["canvas"]["width"], recipe["canvas"]["height"]),
            Image.Resampling.LANCZOS,
        )

    source_root = package_root / "source" / weather
    export_root = package_root / "export" / weather
    preview_root = package_root / "preview" / weather
    stack_root = package_root / "source/stack_frames"
    for path in (source_root / "masks", export_root, preview_root, stack_root):
        path.mkdir(parents=True, exist_ok=True)

    master_path = source_root / "approved_master.png"
    save_png(master.convert("RGBA"), master_path)
    fragment = {
        "schema_version": recipe["schema_version"],
        "weather": weather,
        "canvas": recipe["canvas"],
        "safe_areas": recipe["safe_areas"],
        "layers": recipe["layers"],
        **source,
    }
    (source_root / "layer_recipe.json").write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    master_array = np.asarray(master, dtype=np.uint8)
    boundaries = interpolate_boundaries(source["boundaries"], master.width, master.height)
    owner = ownership_map(boundaries, master.width, master.height)
    palette = np.array(
        [[65,105,225],[100,149,237],[123,104,238],[72,61,139],[46,139,87],[205,133,63],[220,20,60]],
        dtype=np.uint8,
    )
    ownership_image = Image.fromarray(palette[owner], mode="RGB")
    save_png(ownership_image, source_root / "ownership_map.png")

    layer_images: list[tuple[str, Image.Image]] = []
    rows: list[dict[str, str]] = []
    for layer in recipe["layers"]:
        index = layer["depth_index"]
        layer_image, owner_mask = build_layer(master_array, boundaries, index, recipe["canvas"]["hidden_bleed_px"])
        mask_path = source_root / "masks" / f"{layer['name']}.png"
        output_path = export_root / f"{weather}__{layer['name']}.png"
        save_png(owner_mask, mask_path)
        save_png(layer_image, output_path)
        layer_images.append((layer["name"], layer_image))
        rows.append(manifest_row(weather, layer, source, output_path, candidate_id))

    recomposite = Image.new("RGBA", master.size, (0, 0, 0, 0))
    for _, layer_image in layer_images:
        recomposite = Image.alpha_composite(recomposite, layer_image)
    expected = np.asarray(master.convert("RGBA"), dtype=np.uint8)
    actual = np.asarray(recomposite, dtype=np.uint8)
    difference = np.abs(expected.astype(np.int16) - actual.astype(np.int16)).astype(np.uint8)
    if np.any(difference):
        raise ValueError(f"recomposition drift: {weather}, max channel difference={int(difference.max())}")

    save_png(recomposite, preview_root / "recomposite.png")
    save_png(Image.fromarray(difference, mode="RGBA"), preview_root / "difference.png")
    alpha_items = [(name, image.getchannel("A").convert("RGB")) for name, image in layer_images]
    alpha_items.append(("ownership", ownership_image))
    save_png(contact_sheet(alpha_items, (480, 270)), preview_root / "alpha_contact_sheet.png")
    board = checkerboard(master.size, 48)
    solo_items = [(name, Image.alpha_composite(board, image)) for name, image in layer_images]
    solo_items.append(("recomposite", recomposite))
    save_png(contact_sheet(solo_items, (480, 270)), preview_root / "solo_layers.png")
    save_png(safe_area_preview(master, recipe["safe_areas"]), preview_root / "safe_area_overlay.png")
    stack_frames = write_stack_frames(weather, layer_images, stack_root)
    summary = {
        "weather": weather,
        "selected_direction": source["selected_direction"],
        "source_sha256": source["source_sha256"],
        "approved_master_sha256": sha256_file(master_path),
        "recomposition_exact": True,
        "layer_count": len(layer_images),
        "structure_invariant": source["structure_invariant"],
    }
    return rows, stack_frames, summary


def write_asset_manifest(rows: list[dict[str, str]], package_root: Path) -> Path:
    path = package_root / "asset_manifest.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_package_manifest(package_root: Path, weather_summaries: list[dict], candidate_id: str) -> Path:
    files = []
    for path in sorted(item for item in package_root.rglob("*") if item.is_file() and item.name != "package_manifest.json"):
        files.append(
            {
                "path": path.relative_to(package_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = {
        "schema_version": "1.0",
        "task_id": "V-04",
        "gate_id": "H3_LAYERABLE_BACKGROUND_REBUILD",
        "candidate_id": candidate_id,
        "status": "READY_FOR_MACHINE_VALIDATION",
        "asset_status": "PENDING_G02_CLEARANCE",
        "formal_use_allowed": False,
        "canvas": {"width": 3840, "height": 2160, "mode": "RGBA"},
        "build_inputs": {
            "generator_sha256": sha256_file(Path(__file__).resolve()),
            "recipe_sha256": sha256_file(RECIPE_PATH),
            "python": sys.version.split()[0],
            "pillow": Image.__version__,
            "numpy": np.__version__,
        },
        "weather_summaries": weather_summaries,
        "file_count": len(files),
        "files": files,
    }
    path = package_root / "package_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def write_tracked_review_bundle(package_root: Path, candidate_id: str, package_manifest: Path) -> Path:
    review_root = HERE / "review/H3" / candidate_id
    if review_root.exists() and any(review_root.iterdir()):
        raise FileExistsError(f"tracked review output already exists and is not empty: {review_root}")
    review_root.mkdir(parents=True, exist_ok=True)
    evidence = []
    for weather in ("storm", "heat", "snow", "fade"):
        for name, size in (
            ("alpha_contact_sheet", (1920, 540)),
            ("solo_layers", (1920, 540)),
            ("safe_area_overlay", (1920, 1080)),
        ):
            source = package_root / "preview" / weather / f"{name}.png"
            output = review_root / f"{weather}__{name}.jpg"
            with Image.open(source) as image:
                image.convert("RGB").resize(size, Image.Resampling.LANCZOS).save(
                    output, format="JPEG", quality=92, optimize=True, progressive=True
                )
            evidence.append(
                {
                    "path": output.relative_to(HERE).as_posix(),
                    "sha256": sha256_file(output),
                    "source_path": source.relative_to(ROOT).as_posix(),
                    "source_sha256": sha256_file(source),
                    "use": name,
                    "weather": weather,
                }
            )
    package = json.loads(package_manifest.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "srp.v04.h3.review-bundle.v1.0",
        "candidate_id": candidate_id,
        "package_manifest_sha256": sha256_file(package_manifest),
        "status": "PENDING_TEAM_DIRECTOR",
        "evidence": evidence,
        "full_resolution_exports": [
            {"path": row["path"], "sha256": row["sha256"]}
            for row in package["files"]
            if row["path"].startswith("export/")
        ],
    }
    manifest = review_root / "review_manifest.json"
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", help="Repository-relative output below .artifacts-local/V-04/H3/layerable-background-rebuild")
    parser.add_argument("--candidate-id", help="Immutable candidate identity; defaults to the output directory name")
    parser.add_argument("--tracked-review", action="store_true", help="Write the hash-bound lightweight review bundle under review/H3")
    args = parser.parse_args()
    output = resolve_output(args.output_root)
    candidate_id = args.candidate_id or output.name
    if not re.fullmatch(r"layer-export-candidate-v[1-9][0-9]*", candidate_id):
        raise ValueError("candidate-id must match layer-export-candidate-vN")
    if output.name != candidate_id:
        raise ValueError("output directory name must equal candidate-id")
    output.mkdir(parents=True, exist_ok=True)
    recipe = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))

    all_rows: list[dict[str, str]] = []
    all_frames: list[Path] = []
    summaries: list[dict] = []
    for weather in WEATHER_ORDER:
        rows, frames, summary = build_weather(recipe, weather, output, candidate_id)
        all_rows.extend(rows)
        all_frames.extend(frames)
        summaries.append(summary)
    write_asset_manifest(all_rows, output)
    review_video = write_review_video(all_frames, output)
    manifest = write_package_manifest(output, summaries, candidate_id)
    review_manifest = write_tracked_review_bundle(output, candidate_id, manifest) if args.tracked_review else None
    result = {
        "result": "PASS",
        "output_root": output.relative_to(ROOT).as_posix(),
        "weather_count": len(summaries),
        "layer_count": len(all_rows),
        "review_video": review_video.relative_to(ROOT).as_posix(),
        "package_manifest": manifest.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256_file(manifest),
        "review_manifest": review_manifest.relative_to(ROOT).as_posix() if review_manifest else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
