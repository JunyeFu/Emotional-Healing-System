from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "materials"
FORBIDDEN_BLIND_TOKENS = {
    "storm",
    "heat",
    "snow",
    "fade",
    "scene_native",
    "abstract_pacer",
    "暴雨",
    "热浪",
    "降雪",
    "褪色",
    "圆环",
    "进度条",
}
BLIND_MARKDOWN_FILES = (
    "02_盲态独立重建任务书.md",
    "05_盲态材料母版与编号方案.md",
)


def repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("REPOSITORY_ROOT_NOT_FOUND")


def load_json(name: str) -> dict:
    return json.loads((MATERIALS / name).read_text(encoding="utf-8"))


def read_csv(name: str) -> list[dict[str, str]]:
    with (MATERIALS / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_materials() -> list[str]:
    errors: list[str] = []
    contract = json.loads((ROOT / "framework_contract_v1.0.json").read_text(encoding="utf-8"))
    evidence = load_json("project_evidence_matrix_v1.0.json")
    tasks = load_json("reconstruction_tasks_v1.0.json")
    assignments = read_csv("blind_assignment_template_v1.0.csv")
    items = read_csv("expert_item_bank_v1.0.csv")
    fixture = json.loads(
        (ROOT / "fixtures" / "synthetic_fixture_report.json").read_text(encoding="utf-8")
    )

    if fixture["material_validation"]["result"] != "PASS":
        errors.append("SYNTHETIC_REPORT_RESULT_NOT_PASS")
    if fixture["material_validation"].get("open_findings"):
        errors.append("SYNTHETIC_REPORT_OPEN_FINDINGS")

    if tuple(contract["blind_material_files"]) != BLIND_MARKDOWN_FILES:
        errors.append("BLIND_MARKDOWN_FILE_SET_MISMATCH")
    for relative in BLIND_MARKDOWN_FILES:
        blind_payload = (ROOT / relative).read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_BLIND_TOKENS:
            if token.lower() in blind_payload:
                errors.append(f"BLIND_MARKDOWN_IDENTITY_LEAK:{relative}:{token}")

    contract_items = [item["id"] for item in contract["expert_items"]]
    if [row["item_id"] for row in items] != contract_items:
        errors.append("EXPERT_ITEM_BANK_MISMATCH")
    if evidence["expert_item_ids"] != contract_items:
        errors.append("EVIDENCE_ITEM_IDS_MISMATCH")

    repo = repository_root()
    for relative in evidence["authority_precedence"]:
        if not (repo / relative).is_file():
            errors.append(f"AUTHORITY_FILE_MISSING:{relative}")

    task_ids = [task["id"] for task in tasks["tasks"]]
    contract_task_ids = [task["id"] for task in contract["reconstruction_tasks"]]
    if task_ids != contract_task_ids:
        errors.append("RECONSTRUCTION_TASK_MISMATCH")
    for task in tasks["tasks"]:
        events = task["events"]
        times = [event["t"] for event in events]
        if times != sorted(times) or times[-1] != task["duration_seconds"]:
            errors.append(f"EVENT_TIMELINE_INVALID:{task['id']}")
        states = {event["availability"] for event in events}
        if not set(task["required_states"]).issubset(states):
            errors.append(f"REQUIRED_STATE_MISSING:{task['id']}")
        if not set(task["keyframes_seconds"]).issubset(times):
            errors.append(f"KEYFRAME_NOT_IN_TIMELINE:{task['id']}")
        last_usable_trend = None
        for event in events:
            unavailable = event["availability"] in {"UNUSABLE", "DISCONNECTED"}
            if unavailable and event["response"] is not None:
                errors.append(f"UNAVAILABLE_RESPONSE_NOT_NULL:{task['id']}:{event['t']}")
            if unavailable and last_usable_trend is not None and event["trend"] != last_usable_trend:
                errors.append(f"UNAVAILABLE_TREND_NOT_FROZEN:{task['id']}:{event['t']}")
            if not unavailable:
                last_usable_trend = event["trend"]
        blind_payload = json.dumps(task, ensure_ascii=False).lower()
        for token in FORBIDDEN_BLIND_TOKENS:
            if token.lower() in blind_payload:
                errors.append(f"BLIND_IDENTITY_LEAK:{task['id']}:{token}")

    expected_designers = ["D01", "D02", "D03", "D04"]
    if [row["designer_code"] for row in assignments] != expected_designers:
        errors.append("ASSIGNMENT_DESIGNER_SET_MISMATCH")
    valid_orders = {("M-A", "M-B"), ("M-B", "M-A")}
    orders = [(row["first_material"], row["second_material"]) for row in assignments]
    if any(order not in valid_orders for order in orders) or orders.count(("M-A", "M-B")) != 2:
        errors.append("ASSIGNMENT_NOT_COUNTERBALANCED")

    return errors


def main() -> int:
    errors = validate_materials()
    if errors:
        print("\n".join(errors))
        return 1
    print("Q01_MATERIALS_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
