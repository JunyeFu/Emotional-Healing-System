#!/usr/bin/env python3
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "00_第五步总说明.md",
    "01_华南理工伦理申报路径核验说明.md",
    "02_伦理审查申请书草案.md",
    "03_完整研究方案摘要.md",
    "04_参与者知情同意书.md",
    "05_敏感个人信息单独同意书.md",
    "06_招募广告.md",
    "07_安全筛查表.md",
    "08_LevelA专家审查说明与评分指南.md",
    "11_LevelB认知访谈脚本.md",
    "13_LevelC技术预试SOP.md",
    "14_实验员双访视SOP.md",
    "16_不良事件与中止记录表.md",
    "17_协议偏离与版本变更表.md",
    "18_会话研究记录表_CRF.md",
    "19_LevelC数据质量报告模板.json",
    "20_研究人员培训与授权记录.md",
    "21_参与者结束说明.md",
    "22_伦理提交检查清单.md",
    "23_材料字段字典.md",
    "forms/09_SCCI_CVI评分表.csv",
    "forms/10_两条件等信息量专家审查表.csv",
    "forms/12_LevelB记录与编码表.csv",
    "forms/15_访视检查清单.csv",
]

def main():
    errors = []
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            errors.append(f"Missing: {rel}")

    consent = (ROOT / "04_参与者知情同意书.md").read_text(encoding="utf-8")
    for phrase in ["参加完全自愿", "随时退出", "可能的不适", "隐私保护", "联系方式"]:
        if phrase not in consent:
            errors.append(f"Consent missing required concept: {phrase}")

    sensitive = (ROOT / "05_敏感个人信息单独同意书.md").read_text(encoding="utf-8")
    if "单独选择" not in sensitive:
        errors.append("Sensitive information consent lacks separate choices.")

    qc = json.loads((ROOT / "19_LevelC数据质量报告模板.json").read_text(encoding="utf-8"))
    if qc.get("sample", {}).get("planned") != 24:
        errors.append("Level C planned sample is not 24.")

    cvi_rows = list(csv.DictReader((ROOT / "forms/09_SCCI_CVI评分表.csv").open(encoding="utf-8-sig")))
    if len(cvi_rows) != 40:
        errors.append(f"Expected 40 SCCI CVI rows, got {len(cvi_rows)}.")

    placeholders = 0
    for p in ROOT.glob("*.md"):
        placeholders += p.read_text(encoding="utf-8").count("[待填写")
    if placeholders == 0:
        errors.append("No placeholders found; institution-specific fields may have been silently invented.")

    status = "PASS" if not errors else "FAIL"
    report = {
        "status": status,
        "errors": errors,
        "institution_specific_placeholders": placeholders,
        "note": "PASS means structural completeness only, not ethics approval."
    }
    (ROOT / "VALIDATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)

if __name__ == "__main__":
    main()
