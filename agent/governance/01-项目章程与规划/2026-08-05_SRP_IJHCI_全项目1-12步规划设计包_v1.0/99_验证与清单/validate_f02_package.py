"""Validate the F-02 candidate package, acceptance record, and task state."""

from __future__ import annotations

import csv
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "03_步骤02_构念比较条件与测量" / "01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md"
ACCEPTANCE = ROOT / "03_步骤02_构念比较条件与测量" / "02_F-02_验收记录.md"
REGISTRY = ROOT / "24_团队任务与项目治理" / "05_可领取任务包.csv"
FORBIDDEN = ("诊断", "治疗", "疾病", "患者", "医疗设备", "临床")
ITEM_IDS = ("S1", "S2", "S3", "S4", "C-T1", "C-T2", "C-A1", "C-A2", "C-C1", "C-C2", "C-D1", "C-D2")
REQUIRED_MARKERS = (
    "CANDIDATE_NOT_LEVEL_AB_VALIDATED",
    "SCCI操纵检查候选",
    "条件中性四层理解题",
    "心智努力候选",
    "五分钟问卷预算",
    "Level A专家审查材料",
    "Level B两条件认知访谈",
    "项目功能与条件间差异审计",
    "失败与降级规则",
    "向R-01交付",
    "向W-01交付",
    "E0D5883163227B60F144085FF250F9A8E4D09A7562CC6EB5244D4CE60E05AB01",
)


def main() -> int:
    errors: list[str] = []
    for path in (PACKAGE, ACCEPTANCE):
        if not path.is_file():
            errors.append(f"missing file: {path}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    package_text = PACKAGE.read_text(encoding="utf-8-sig")
    acceptance_text = ACCEPTANCE.read_text(encoding="utf-8-sig")
    combined = package_text + "\n" + acceptance_text

    for marker in REQUIRED_MARKERS:
        if marker not in package_text:
            errors.append(f"package missing marker {marker!r}")
    for item_id in ITEM_IDS:
        if not re.search(rf"\| {re.escape(item_id)} \|", package_text):
            errors.append(f"package missing item {item_id}")
    for marker in ("PASS_FOR_CANDIDATE_PACKAGE", "AC1", "AC2", "AC3", "F-02=DONE"):
        if marker not in acceptance_text:
            errors.append(f"acceptance missing marker {marker!r}")

    if re.search(r"turn\d+(?:file|search)", combined, flags=re.IGNORECASE):
        errors.append("unusable turn citation found")
    if "sandbox:/" in package_text:
        errors.append("package contains a sandbox link")
    for term in FORBIDDEN:
        if term in combined:
            errors.append(f"restricted term found: {term}")

    scci_start = package_text.index("## 4. SCCI操纵检查候选")
    scci_end = package_text.index("## 5. 条件中性四层理解题")
    primary_table = package_text[scci_start:scci_end].split("### 4.2", maxsplit=1)[0]
    for contamination in ("容易", "清楚", "有效", "成功", "喜欢", "舒适"):
        if re.search(rf"\| S[1-4] \|[^\n]*{contamination}", primary_table):
            errors.append(f"SCCI primary item contains contamination term {contamination!r}")

    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["task_id"]: row for row in csv.DictReader(handle)}
    if rows.get("F-02", {}).get("status") != "DONE":
        errors.append("F-02 must remain DONE")
    for task_id in ("G-01", "R-01"):
        actual = rows.get(task_id, {}).get("status")
        if actual not in {"READY", "DONE"}:
            errors.append(f"{task_id} status is {actual!r}, expected READY or DONE")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("PASS: F-02 candidate package; AC1-AC3; items=12; F-02=DONE; downstream unblocked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
