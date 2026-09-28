#!/usr/bin/env python3
"""Validate the local V-04 H3 4K transparent-layer candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


WEATHERS = ("storm", "heat", "snow", "fade")
LAYERS = (
    "sky_clouds",
    "far_landform_01",
    "far_landform_02",
    "far_landform_03",
    "mid_terrain",
    "ground_visual",
    "foreground_occluders",
)
SIZE = (3840, 2160)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_repo(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


class Checks:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def add(self, check_id: str, passed: bool, detail: str) -> None:
        self.items.append({"id": check_id, "status": "PASS" if passed else "FAIL", "detail": detail})

    @property
    def passed(self) -> bool:
        return all(item["status"] == "PASS" for item in self.items)


def composite(paths: list[Path]) -> Image.Image:
    image = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    for path in paths:
        with Image.open(path) as layer:
            image = Image.alpha_composite(image, layer.convert("RGBA"))
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    repo = find_repo(Path(__file__).resolve())
    candidate = args.candidate.resolve()
    checks = Checks()
    required = ("package_manifest.json", "asset_manifest.csv", "source", "export", "preview")
    checks.add("H3-001", all((candidate / name).exists() for name in required), "required candidate paths exist")
    if not checks.passed:
        return emit(args.report, candidate, checks)

    package = json.loads((candidate / "package_manifest.json").read_text(encoding="utf-8"))
    checks.add("H3-002", package.get("status") == "READY_FOR_MACHINE_VALIDATION", "candidate status is machine-validation only")
    checks.add("H3-003", package.get("formal_use_allowed") is False, "formal use remains blocked")
    checks.add("H3-016", package.get("candidate_id") == candidate.name, "candidate identity matches the immutable directory name")

    recipe_path = Path(__file__).resolve().parent / "V-04_H3_透明分层配方_v1.0.json"
    generator_path = Path(__file__).resolve().parent / "build_v04_h3_layer_exports.py"
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    build_inputs = package.get("build_inputs", {})
    checks.add(
        "H3-017",
        build_inputs.get("recipe_sha256") == sha256(recipe_path)
        and build_inputs.get("generator_sha256") == sha256(generator_path),
        "package binds the current recipe and generator hashes",
    )

    rows = list(csv.DictReader((candidate / "asset_manifest.csv").open(encoding="utf-8-sig", newline="")))
    checks.add("H3-004", len(rows) == 28, f"asset rows={len(rows)} expected=28")
    pairs = {(row.get("scene"), row.get("layer_role")) for row in rows}
    expected_pairs = {(weather, layer) for weather in WEATHERS for layer in LAYERS}
    checks.add("H3-005", pairs == expected_pairs, "manifest covers every weather-layer pair exactly once")
    checks.add(
        "H3-006",
        all(row.get("status") == "PENDING_G02_CLEARANCE" and row.get("formal_use_allowed") == "false" for row in rows),
        "all assets retain the G-02 release boundary",
    )

    export_paths: list[Path] = []
    image_checks = True
    alpha_checks = True
    hash_checks = True
    for row in rows:
        path = candidate / "export" / row["scene"] / f"{row['scene']}__{row['layer_role']}.png"
        export_paths.append(path)
        if not path.is_file():
            image_checks = alpha_checks = hash_checks = False
            continue
        hash_checks &= sha256(path) == row.get("final_sha256")
        with Image.open(path) as image:
            image_checks &= image.size == SIZE and image.mode == "RGBA"
            rgba = np.asarray(image)
        alpha = rgba[:, :, 3]
        values = set(np.unique(alpha).tolist())
        if row["layer_role"] == "sky_clouds":
            alpha_checks &= values == {255}
        else:
            alpha_checks &= values == {0, 255}
        alpha_checks &= not np.any(rgba[:, :, :3][alpha == 0])
    checks.add("H3-007", image_checks, "all 28 exports are 3840x2160 RGBA PNG")
    checks.add("H3-008", alpha_checks, "alpha is binary, non-sky layers are transparent, transparent RGB is zero")
    checks.add("H3-009", hash_checks, "asset-manifest hashes match export bytes")

    masks_ok = True
    for weather in WEATHERS:
        masks = []
        for layer in LAYERS:
            path = candidate / "source" / weather / "masks" / f"{layer}.png"
            if not path.is_file():
                masks_ok = False
                continue
            with Image.open(path) as image:
                masks_ok &= image.size == SIZE and image.mode == "L"
                masks.append(np.asarray(image) > 0)
        if len(masks) == 7:
            count = np.sum(np.stack(masks, axis=0), axis=0)
            masks_ok &= bool(np.all(count == 1))
    checks.add("H3-010", masks_ok, "ownership masks are exclusive and cover the full canvas")

    recomposite_ok = True
    source_ok = True
    for weather in WEATHERS:
        master = candidate / "source" / weather / "approved_master.png"
        layers = [candidate / "export" / weather / f"{weather}__{layer}.png" for layer in LAYERS]
        if not master.is_file() or not all(path.is_file() for path in layers):
            recomposite_ok = source_ok = False
            continue
        with Image.open(master) as image:
            source_ok &= image.size == SIZE and image.mode == "RGBA"
            expected = np.asarray(image)
        actual = np.asarray(composite(layers))
        recomposite_ok &= bool(np.array_equal(expected, actual))
    checks.add("H3-011", source_ok, "four approved masters are normalized to 4K RGBA")
    checks.add("H3-012", recomposite_ok, "ordered layer recomposition is byte-exact to each approved master")

    listed = package.get("files", [])
    package_hashes_ok = all((candidate / item["path"]).is_file() and sha256(candidate / item["path"]) == item["sha256"] for item in listed)
    ignored_outputs = {"package_manifest.json", "validation_report.json"}
    if args.report and args.report.resolve().parent == candidate:
        ignored_outputs.add(args.report.resolve().name)
    actual = {
        path.relative_to(candidate).as_posix()
        for path in candidate.rglob("*")
        if path.is_file() and path.name not in ignored_outputs
    }
    declared = {item["path"] for item in listed}
    checks.add("H3-013", package_hashes_ok and actual == declared, f"package inventory files={len(actual)}")

    relative = candidate.relative_to(repo).as_posix() if candidate.is_relative_to(repo) else ""
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative], cwd=repo, check=False
    ).returncode == 0 if relative else False
    tracked = subprocess.run(
        ["git", "ls-files", "--", relative], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip() if relative else "outside-repo"
    checks.add("H3-014", ignored and not tracked, "4K candidate is git-ignored and untracked")

    review_files = [
        candidate / "preview" / weather / "alpha_contact_sheet.png" for weather in WEATHERS
    ] + [candidate / "preview" / weather / "solo_layers.png" for weather in WEATHERS]
    checks.add("H3-015", all(path.is_file() for path in review_files), "eight required human-review sheets exist")
    lineage_ok = True
    for weather in WEATHERS:
        source = recipe["weathers"][weather]
        source_path = repo / source["source_path"]
        derived_recipe = json.loads((candidate / "source" / weather / "layer_recipe.json").read_text(encoding="utf-8"))
        expected_fragment = {
            "schema_version": recipe["schema_version"],
            "weather": weather,
            "canvas": recipe["canvas"],
            "safe_areas": recipe["safe_areas"],
            "layers": recipe["layers"],
            **source,
        }
        lineage_ok &= source_path.is_file() and sha256(source_path) == source["source_sha256"]
        lineage_ok &= derived_recipe == expected_fragment
        if source_path.is_file():
            with Image.open(source_path) as image:
                normalized = image.convert("RGB").resize(SIZE, Image.Resampling.LANCZOS).convert("RGBA")
            with Image.open(candidate / "source" / weather / "approved_master.png") as image:
                lineage_ok &= bool(np.array_equal(np.asarray(normalized), np.asarray(image.convert("RGBA"))))
    checks.add("H3-018", lineage_ok, "frozen source bytes, derived recipes and normalized masters match authority")
    return emit(args.report, candidate, checks)


def emit(report_path: Path | None, candidate: Path, checks: Checks) -> int:
    payload = {
        "schema_version": "srp.v04.h3.validation.v1.0",
        "candidate": candidate.relative_to(find_repo(Path(__file__).resolve())).as_posix(),
        "status": "PASS" if checks.passed else "FAIL",
        "checks": checks.items,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if report_path:
        if report_path.exists():
            raise FileExistsError(f"report already exists: {report_path}")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if checks.passed else 1


if __name__ == "__main__":
    sys.exit(main())
