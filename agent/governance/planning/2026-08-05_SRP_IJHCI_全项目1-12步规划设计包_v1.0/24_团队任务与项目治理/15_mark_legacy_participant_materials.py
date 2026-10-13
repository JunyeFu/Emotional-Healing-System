"""Mark every v1.0 participant-facing material as non-executable history."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = (
    ROOT
    / "90_既有执行材料"
    / "2026-08-05_SRP_IJHCI_第五步伦理与预试材料包_v1.0"
)
MARKER = (
    "> **SUPERSEDED / NOT_FOR_RECRUITMENT / NOT_FOR_SUBMISSION**\n"
    "> 本v1.0材料仅作迁移与审计证据；它仍含旧流程和待关闭字段。"
    "必须完成G-01、双人逐字段复核及外部门禁后，才能使用新的v1.1材料。\n"
)


def marked(content: str) -> bool:
    return "SUPERSEDED / NOT_FOR_RECRUITMENT / NOT_FOR_SUBMISSION" in content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    paths = sorted(LEGACY.glob("*.md"))
    missing = [path for path in paths if not marked(path.read_text(encoding="utf-8-sig"))]
    if args.check:
        for path in missing:
            print(f"ERROR: missing legacy marker: {path.name}")
        if missing:
            return 1
        print(f"PASS: legacy participant materials marked={len(paths)}")
        return 0

    for path in missing:
        content = path.read_text(encoding="utf-8-sig")
        lines = content.splitlines()
        if lines:
            content = lines[0] + "\n\n" + MARKER + "\n" + "\n".join(lines[1:])
        else:
            content = MARKER
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        print(f"MARKED: {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
