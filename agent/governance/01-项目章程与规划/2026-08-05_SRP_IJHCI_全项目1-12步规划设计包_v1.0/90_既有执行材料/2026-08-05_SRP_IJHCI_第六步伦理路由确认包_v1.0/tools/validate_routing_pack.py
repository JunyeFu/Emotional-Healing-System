#!/usr/bin/env python3
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    required = [
        "00_第六步总说明.md",
        "01_官方证据与边界备忘录.md",
        "02_伦理路由决策树.md",
        "03_联系导师与科研秘书的正式询问稿.md",
        "04_一页式伦理路由摘要.md",
        "05_伦理路由会议清单.md",
        "06_伦理路由确认记录.md",
        "07_待关闭字段矩阵.md",
        "08_伦理提交附件目录.md",
        "09_当前路由决定与下一门.md",
        "forms/伦理路由问题清单.csv",
    ]
    errors = []
    for rel in required:
        if not (root / rel).exists():
            errors.append(f"Missing {rel}")

    rows = list(csv.DictReader(
        (root / "forms" / "伦理路由问题清单.csv").open(encoding="utf-8-sig")
    ))
    if len(rows) != 20:
        errors.append(f"Expected 20 routing questions, got {len(rows)}")
    if any(row["status"] != "UNCONFIRMED" for row in rows):
        errors.append("Questions must stay UNCONFIRMED until an institutional reply.")

    text = (root / "01_官方证据与边界备忘录.md").read_text(encoding="utf-8")
    for phrase in ["特定基金批次", "不能直接复制", "未确认"]:
        if phrase not in text:
            errors.append(f"Evidence memo missing boundary phrase: {phrase}")

    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "routing_confirmed": False,
        "formal_participant_recruitment_allowed": False,
        "note": "Structural pass only. Institutional confirmation is required."
    }
    (root / "VALIDATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)

if __name__ == "__main__":
    main()
