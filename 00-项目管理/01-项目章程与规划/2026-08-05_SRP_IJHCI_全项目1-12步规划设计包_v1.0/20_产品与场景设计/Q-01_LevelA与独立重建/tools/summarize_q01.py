from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "framework_contract_v1.0.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(row: dict[str, str], field: str) -> int:
    return int(row[field])


def expected_people(contract: dict) -> dict[str, Counter]:
    roles = contract["roles"]
    return {
        "expert": Counter(roles["expert"]["role_groups"]),
        "designer": Counter(roles["designer"]["role_groups"]),
        "rater": Counter({"__total__": roles["rater"]["count"]}),
    }


def validate_roster(rows: list[dict[str, str]], contract: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    codes = [row.get("person_code", "").strip() for row in rows]
    if not all(codes) or len(codes) != len(set(codes)):
        errors.append("ROSTER_CODE_MISSING_OR_DUPLICATE")

    by_role: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        role = row.get("role", "")
        by_role[role].append(row)
        if row.get("eligible") != "1" or row.get("framework_author") != "0":
            errors.append(f"ROSTER_INELIGIBLE:{row.get('person_code', '')}")

    expected = expected_people(contract)
    for role in ("expert", "designer"):
        actual = Counter(row.get("role_group", "") for row in by_role[role])
        if actual != expected[role]:
            errors.append(f"ROSTER_ROLE_GROUP_MISMATCH:{role}")
    if len(by_role["rater"]) != expected["rater"]["__total__"]:
        errors.append("ROSTER_RATER_COUNT_MISMATCH")
    if set(by_role) - {"expert", "designer", "rater"}:
        errors.append("ROSTER_UNKNOWN_ROLE")
    return not errors, errors


def evaluate_experts(
    roster: list[dict[str, str]], rows: list[dict[str, str]], contract: dict
) -> dict:
    expert_codes = {row["person_code"] for row in roster if row["role"] == "expert"}
    item_ids = {item["id"] for item in contract["expert_items"]}
    pairs = [(row.get("reviewer_code", ""), row.get("item_id", "")) for row in rows]
    expected_pairs = {(code, item) for code in expert_codes for item in item_ids}
    complete = set(pairs) == expected_pairs and len(pairs) == len(expected_pairs)
    valid_scores = True
    blockers = 0
    by_item: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        try:
            scores = [as_int(row, field) for field in (
                "relevance", "comprehensiveness", "clarity", "construct_purity"
            )]
            blocker = as_int(row, "critical_blocker")
        except (KeyError, ValueError):
            valid_scores = False
            continue
        if any(score not in {1, 2, 3, 4} for score in scores) or blocker not in {0, 1}:
            valid_scores = False
        blockers += blocker
        by_item[row.get("item_id", "")].append(row)

    i_cvi: dict[str, float] = {}
    if complete and valid_scores:
        minimum = contract["expert_gate"]["valid_score_min"]
        for item_id in sorted(item_ids):
            values = by_item[item_id]
            i_cvi[item_id] = sum(as_int(row, "relevance") >= minimum for row in values) / len(values)
    s_cvi = mean(i_cvi.values()) if i_cvi else 0.0
    threshold = contract["expert_gate"]
    passed = (
        complete
        and valid_scores
        and all(value >= threshold["i_cvi_min"] for value in i_cvi.values())
        and s_cvi >= threshold["s_cvi_ave_min"]
        and blockers <= threshold["open_critical_blockers_allowed"]
    )
    return {
        "complete": complete and valid_scores,
        "i_cvi": i_cvi,
        "s_cvi_ave": round(s_cvi, 4),
        "critical_blockers": blockers,
        "passed": passed,
    }


def evaluate_reconstruction(
    roster: list[dict[str, str]], rows: list[dict[str, str]], contract: dict
) -> dict:
    designer_codes = {row["person_code"] for row in roster if row["role"] == "designer"}
    rater_codes = {row["person_code"] for row in roster if row["role"] == "rater"}
    task_ids = {task["id"] for task in contract["reconstruction_tasks"]}
    expected = {
        (designer, task, rater)
        for designer in designer_codes
        for task in task_ids
        for rater in rater_codes
    }
    triples = [
        (row.get("designer_code", ""), row.get("task_id", ""), row.get("rater_code", ""))
        for row in rows
    ]
    complete = set(triples) == expected and len(triples) == len(expected)
    fields = (
        "target_correct",
        "actual_correct",
        "cumulative_correct",
        "fallback_correct",
        "forbidden_coupling",
        "identity_leak",
        "color_only",
    )
    valid_scores = True
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        try:
            values = [as_int(row, field) for field in fields]
        except (KeyError, ValueError):
            valid_scores = False
            continue
        if any(value not in {0, 1} for value in values):
            valid_scores = False
        grouped[(row.get("designer_code", ""), row.get("task_id", ""))].append(row)

    disagreements: list[str] = []
    output_pass: dict[tuple[str, str], bool] = {}
    if complete and valid_scores:
        for key, ratings in grouped.items():
            if len(ratings) != contract["reconstruction_gate"]["raters_per_output"]:
                complete = False
                continue
            if any(len({row[field] for row in ratings}) != 1 for field in fields):
                disagreements.append(f"{key[0]}:{key[1]}")
                continue
            first = ratings[0]
            layers_ok = all(as_int(first, field) == 1 for field in fields[:4])
            violations_absent = all(as_int(first, field) == 0 for field in fields[4:])
            output_pass[key] = layers_ok and violations_absent

    designers_passing_both = sum(
        all(output_pass.get((designer, task), False) for task in task_ids)
        for designer in designer_codes
    )
    task_pass_counts = {
        task: sum(output_pass.get((designer, task), False) for designer in designer_codes)
        for task in sorted(task_ids)
    }
    threshold = contract["reconstruction_gate"]
    passed = (
        complete
        and valid_scores
        and not disagreements
        and designers_passing_both >= threshold["designers_passing_both_tasks_min"]
        and all(
            count >= threshold["designers_passing_each_task_min"]
            for count in task_pass_counts.values()
        )
    )
    return {
        "complete": complete and valid_scores,
        "unresolved_disagreements": disagreements,
        "designers_passing_both_tasks": designers_passing_both,
        "task_pass_counts": task_pass_counts,
        "passed": passed,
    }


def evaluate(
    roster: list[dict[str, str]],
    expert_rows: list[dict[str, str]],
    reconstruction_rows: list[dict[str, str]],
    contract: dict,
) -> dict:
    roster_ok, roster_errors = validate_roster(roster, contract)
    expert = evaluate_experts(roster, expert_rows, contract)
    reconstruction = evaluate_reconstruction(roster, reconstruction_rows, contract)
    if not roster_ok or not expert["complete"] or not reconstruction["complete"]:
        decision = "INCOMPLETE"
    elif not expert["passed"] or reconstruction["unresolved_disagreements"]:
        decision = "REVISE"
    elif reconstruction["passed"]:
        decision = "PASS"
    else:
        decision = "DOWNGRADE_TO_FOUR_SCENE_DESIGN_PATTERN"
    return {
        "schema_version": "1.0",
        "task_id": "Q-01",
        "decision": decision,
        "roster": {"passed": roster_ok, "errors": roster_errors},
        "expert_gate": expert,
        "reconstruction_gate": reconstruction,
        "claim_boundary": "MATERIAL_AND_DESIGN_KNOWLEDGE_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Q-01 Level A and reconstruction records")
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--expert", type=Path, required=True)
    parser.add_argument("--reconstruction", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    result = evaluate(
        read_csv(args.roster),
        read_csv(args.expert),
        read_csv(args.reconstruction),
        contract,
    )
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
