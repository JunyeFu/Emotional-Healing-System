#!/usr/bin/env python3
"""Validate independent V-04 H3 assets and build a derived review sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


COLS = 4
ROWS = 2
CELL = 512
MARGIN = 64
ALPHA_THRESHOLD = 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkerboard(size: tuple[int, int], tile: int = 24) -> Image.Image:
    image = Image.new("RGB", size, (224, 224, 224))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(248, 248, 248))
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--weather", choices=("storm", "heat", "snow", "fade"), required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")
    authority = json.loads(args.authority.read_text(encoding="utf-8"))
    expected = authority["weather_assets"][args.weather]
    if len(expected) != COLS * ROWS:
        raise SystemExit("weather asset count must be exactly eight")

    sheet = Image.new("RGBA", (COLS * CELL, ROWS * CELL))
    records = []
    for index, item in enumerate(expected):
        path = args.assets / f"{args.weather}__{item['id']}.png"
        if not path.is_file():
            raise SystemExit(f"missing asset: {path.name}")
        with Image.open(path) as source:
            if source.mode != "RGBA":
                raise SystemExit(f"asset is not RGBA: {path.name}")
            image = source.copy()
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] != 0 or alpha.getextrema()[1] == 0:
            raise SystemExit(f"asset lacks usable alpha: {path.name}")
        corners = (alpha.getpixel((0, 0)), alpha.getpixel((image.width - 1, 0)), alpha.getpixel((0, image.height - 1)), alpha.getpixel((image.width - 1, image.height - 1)))
        if max(corners) > 1:
            raise SystemExit(f"asset corner is not transparent: {path.name}")
        bbox = alpha.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0).getbbox()
        if bbox is None:
            raise SystemExit(f"asset is empty: {path.name}")
        trimmed = image.crop(bbox)
        scale = min((CELL - 2 * MARGIN) / trimmed.width, (CELL - 2 * MARGIN) / trimmed.height, 1.0)
        if scale < 1.0:
            trimmed = trimmed.resize((max(1, round(trimmed.width * scale)), max(1, round(trimmed.height * scale))), Image.Resampling.LANCZOS)
        col = index % COLS
        row = index // COLS
        x = col * CELL + (CELL - trimmed.width) // 2
        y = row * CELL + (CELL - trimmed.height) // 2
        sheet.alpha_composite(trimmed, (x, y))
        records.append({
            "asset_id": item["id"],
            "role": item["role"],
            "path": path.name,
            "width": image.width,
            "height": image.height,
            "alpha_extrema": list(alpha.getextrema()),
            "sha256": sha256(path),
        })

    args.output.mkdir(parents=True)
    transparent_path = args.output / f"{args.weather}-review-sheet.png"
    checker_path = args.output / f"{args.weather}-review-checker.jpg"
    sheet.save(transparent_path, optimize=True)
    checker = checkerboard(sheet.size)
    checker.paste(sheet, mask=sheet.getchannel("A"))
    checker.save(checker_path, quality=92, optimize=True)
    manifest = {
        "schema_version": "srp.v04.h3.independent-asset-candidate.v1.0",
        "weather": args.weather,
        "status": "READY_FOR_TEAM_DIRECTOR_REVIEW",
        "asset_count": len(records),
        "assets": records,
        "derived_review_sheet": {"path": transparent_path.name, "sha256": sha256(transparent_path)},
        "checker_review": {"path": checker_path.name, "sha256": sha256(checker_path)},
        "asset_status": "PENDING_G02_CLEARANCE",
        "formal_use_allowed": False,
    }
    (args.output / "candidate_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
