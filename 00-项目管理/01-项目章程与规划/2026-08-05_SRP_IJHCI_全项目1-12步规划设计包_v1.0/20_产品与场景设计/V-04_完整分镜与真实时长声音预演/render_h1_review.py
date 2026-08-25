from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
SOURCE = REPO / ".artifacts-local" / "V-04" / "H1" / "candidates"
OUTPUT = HERE / "review" / "H1"
MANIFEST = HERE / "V-04_H1候选清单_v1.0.json"
REPORT = HERE / "V-04_H1评审图清单_v1.0.json"

SCENES = ("storm", "heat", "snow", "fade", "corridor")
CANVAS = (1920, 650)
IMAGE_SIZE = (930, 523)
IMAGE_Y = 110
POSITIONS = ((20, IMAGE_Y), (970, IMAGE_Y))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlay_review_guides(image: Image.Image) -> Image.Image:
    result = image.copy()
    draw = ImageDraw.Draw(result)
    width, height = result.size

    def box(bounds: tuple[float, float, float, float], color: tuple[int, int, int]) -> None:
        x0, y0, x1, y1 = bounds
        draw.rectangle(
            (
                round(x0 * width),
                round((1 - y1) * height),
                round(x1 * width),
                round((1 - y0) * height),
            ),
            outline=color,
            width=3,
        )

    box((0.20, 0.18, 0.45, 0.52), (63, 211, 255))
    box((0.55, 0.34, 0.85, 0.72), (109, 255, 140))
    horizon = round((1 - 0.59) * height)
    draw.line((0, horizon, width, horizon), fill=(255, 215, 80), width=2)
    return result


def centered_x(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, center: int) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return center - (right - left) // 2


def main() -> None:
    source_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_id = {item["candidate_id"]: item for item in source_manifest["candidates"]}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=28)
    small = ImageFont.load_default(size=20)
    outputs: list[dict[str, object]] = []

    for scene in SCENES:
        canvas = Image.new("RGB", CANVAS, (22, 25, 29))
        draw = ImageDraw.Draw(canvas)
        title = f"V-04 H1 / {scene.upper()} / REVIEW OVERLAY ONLY"
        draw.text((centered_x(draw, title, font, CANVAS[0] // 2), 14), title, font=font, fill=(245, 245, 245))
        legend = "CYAN actual safe area  |  GREEN target safe area  |  YELLOW horizon y=0.59"
        draw.text((centered_x(draw, legend, small, CANVAS[0] // 2), 58), legend, font=small, fill=(205, 210, 215))

        for variant, position in zip(("A", "B"), POSITIONS, strict=True):
            candidate = by_id[f"{scene}-{variant}"]
            source = SOURCE / str(candidate["file"])
            if not source.is_file() or sha256(source) != candidate["sha256"]:
                raise SystemExit(f"candidate hash mismatch: {source}")
            with Image.open(source) as image:
                image = image.convert("RGB").resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
            image = overlay_review_guides(image)
            canvas.paste(image, position)
            draw.rectangle(
                (position[0], position[1], position[0] + IMAGE_SIZE[0] - 1, position[1] + IMAGE_SIZE[1] - 1),
                outline=(235, 235, 235),
                width=2,
            )
            label = f"{scene.upper()} {variant}  SHA {candidate['sha256'][:12]}"
            center = position[0] + IMAGE_SIZE[0] // 2
            draw.text((centered_x(draw, label, small, center), 84), label, font=small, fill=(235, 235, 235))

        output = OUTPUT / f"{scene}-AB-review.jpg"
        canvas.save(output, format="JPEG", quality=92, subsampling=0, optimize=True)
        outputs.append(
            {
                "scene_id": scene,
                "file": output.relative_to(HERE).as_posix(),
                "width": CANVAS[0],
                "height": CANVAS[1],
                "sha256": sha256(output),
                "review_overlay_only": True,
            }
        )

    report = {
        "schema_version": "1.0",
        "task_id": "V-04",
        "gate_id": "H1",
        "source_manifest_sha256": sha256(MANIFEST),
        "outputs": outputs,
        "selection_status": "PENDING_HUMAN_CONFIRMATION",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: rendered {len(outputs)} H1 A/B review sheets")


if __name__ == "__main__":
    main()
