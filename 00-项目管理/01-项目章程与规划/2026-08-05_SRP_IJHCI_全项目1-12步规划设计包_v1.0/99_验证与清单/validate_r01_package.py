"""Validate the R-01 candidate package, assets, acceptance, and task state."""

from __future__ import annotations

import csv
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
R01 = ROOT / "20_产品与场景设计" / "R-01_四层表示方案"
PACKAGE = R01 / "R-01_四层候选语法与完整表示方案_v0.9-candidate.md"
ACCEPTANCE = R01 / "R-01_验收记录.md"
SCHEMA = R01 / "r01-four-layer-representation-v0.9.schema.json"
FIXTURES = R01 / "fixtures"
REGISTRY = ROOT / "24_团队任务与项目治理" / "05_可领取任务包.csv"
FORBIDDEN = ("诊断", "治疗", "疾病", "患者", "医疗设备", "临床")
REQUIRED_FILES = (
    PACKAGE,
    ACCEPTANCE,
    SCHEMA,
    FIXTURES / "valid-storm-scene-native.json",
    FIXTURES / "valid-storm-abstract-pacer.json",
    FIXTURES / "invalid-missing-fallback.json",
    FIXTURES / "invalid-coupled-actual.json",
    FIXTURES / "invalid-unusable-behavior.json",
    FIXTURES / "invalid-confound-budget.json",
    FIXTURES / "comprehension-truth-minimal.json",
)
REQUIRED_MARKERS = (
    "四层候选语法与严格操作定义",
    "跨模块统一语法与两种完整表示方案",
    "六类视觉混杂的计算定义与公平审计",
    "条件中性说明与F-02理解题真值接口",
    "R-01验收表",
    "3-3-3-3",
    "4-6",
    "5-5",
    "双吸",
    "运动能量",
    "平均亮度",
    "视觉复杂度",
    "空间偏心",
    "遮挡",
    "事件显著度",
    "66C786349F8AB06CB24DAF438C817BFF16339EF9462778F6C0C97439E8AC0D31",
)


def load_json(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
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
    for marker in ("PASS_FOR_CANDIDATE_PACKAGE", "AC1", "AC2", "AC3", "R-01=DONE"):
        if marker not in acceptance_text:
            errors.append(f"acceptance missing marker {marker!r}")
    if re.search(r"turn\d+(?:file|search|view|academia)", combined, flags=re.IGNORECASE):
        errors.append("unusable internal citation found")
    if "sandbox:/" in combined:
        errors.append("sandbox link found")
    for term in FORBIDDEN:
        if term in combined:
            errors.append(f"restricted term found: {term}")

    try:
        schema = load_json(SCHEMA)
        native = load_json(FIXTURES / "valid-storm-scene-native.json")
        abstract = load_json(FIXTURES / "valid-storm-abstract-pacer.json")
        missing = load_json(FIXTURES / "invalid-missing-fallback.json")
        coupled = load_json(FIXTURES / "invalid-coupled-actual.json")
        unusable = load_json(FIXTURES / "invalid-unusable-behavior.json")
        confound = load_json(FIXTURES / "invalid-confound-budget.json")
        truth = load_json(FIXTURES / "comprehension-truth-minimal.json")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"JSON asset error: {exc}")
    else:
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append("schema is not Draft 2020-12")
        if native.get("cue_mode") != "scene_native":
            errors.append("native fixture has wrong cue_mode")
        if abstract.get("cue_mode") != "abstract_pacer":
            errors.append("abstract fixture has wrong cue_mode")
        invariant_keys = ("timing", "layers", "fallback_contract", "confound_budget")
        for key in invariant_keys:
            if native.get(key) != abstract.get(key):
                errors.append(f"valid conditions differ in invariant field {key}")
        if "fallback" in missing.get("layers", {}):
            errors.append("missing-fallback fixture still contains fallback")
        if coupled.get("layers", {}).get("actual", {}).get("source") != "python.target_protocol":
            errors.append("coupled-actual negative is not targeted")
        unusable_state = unusable.get("fallback_contract", {}).get("UNUSABLE", {})
        if unusable_state.get("actual") != "real" or unusable_state.get("cumulative") != "update":
            errors.append("unusable-behavior negative is not targeted")
        if confound.get("confound_budget", {}).get("motion_energy_relative_difference", 0) <= 0.1:
            errors.append("confound negative does not exceed the candidate budget")
        for key in ("target_phase", "actual_phase", "cumulative_band", "degradation_reason"):
            if key not in truth:
                errors.append(f"truth fixture missing {key}")

    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["task_id"]: row for row in csv.DictReader(handle)}
    expected = {"F-02": "DONE", "R-01": "DONE", "W-01": "READY"}
    for task_id, status in expected.items():
        actual = rows.get(task_id, {}).get("status")
        if actual != status:
            errors.append(f"{task_id} status is {actual!r}, expected {status!r}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "PASS: R-01 candidate package; AC1-AC3; schema+2 valid fixtures+4 negatives; "
        "R-01=DONE; W-01=READY"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
