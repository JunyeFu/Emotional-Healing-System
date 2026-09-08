"""Validate the finite-budget teaching candidate, not participant readiness."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
BREATH = ROOT / "02-技术研发/srp_session_core/config/breath_protocol_config_v2.2.json"
TIMELINE = ["neutral_preparation", "panas_pre", "allocation_reveal",
            "condition_training", "core_800s", "panas_post", "understanding_and_other_measures"]


def validate(contract, breath, record):
    errors = []
    if contract["status"] != "CANDIDATE_NOT_RESEARCH_FROZEN" or (
        contract["formal_training_budget_seconds"] is not None
        or contract["formal_collection_allowed"] is not False
    ):
        errors.append("UNAPPROVED_FREEZE")
    modes = ["scene_native", "abstract_pacer"]
    if contract["conditions"] != modes or contract["native_is_hidden"] is not False:
        errors.append("CONDITION_DEFINITION")
    budget = contract["candidate_budget_seconds"]
    blocks = contract["blocks"]
    if (type(budget) is not int or budget <= 0
        or any(type(b["seconds"]) is not int or b["seconds"] <= 0 for b in blocks)
        or sum(b["seconds"] for b in blocks) != budget
        or contract["arm_budget_seconds"] != dict.fromkeys(modes, budget)):
        errors.append("BUDGET_MISMATCH")
    if [b["id"] for b in blocks] != ["four_layers", "storm", "heat", "snow", "fade", "unavailable", "recap"]:
        errors.append("BLOCK_COVERAGE")
    if contract["timeline"] != TIMELINE:
        errors.append("TIMELINE_ORDER")
    if contract["weather_order"] != "assignment.weather_sequence":
        errors.append("ASSIGNMENT_ORDER")
    if (contract["mastery_based_extension"] is not False
        or contract["exclude_for_slow_learning"] is not False
        or contract["extra_instruction_repetitions"] != 0):
        errors.append("ADAPTIVE_TRAINING_OR_SELECTION")
    if contract["demonstration_cycles_per_weather"] != 1 or contract["practice_cycles_per_weather"] != 1:
        errors.append("CYCLE_BUDGET")
    for b in blocks:
        if b["id"] in breath["modules"]:
            duration = sum(s["duration_seconds"] for s in breath["modules"][b["id"]]["steps"])
            if 2 * duration > b["seconds"]:
                errors.append("CYCLES_DO_NOT_FIT:" + b["id"])
    if (contract["understanding_in_core"] is not False
        or contract["emotion_reporting_requires_understanding_pass"] is not False
        or contract["formal_runtime_mock_allowed"] is not False
        or contract["core_demo_extra_budget"] is not False
        or contract["core_demo_seconds"] != 25):
        errors.append("CORE_OR_EVIDENCE_BOUNDARY")
    if contract["layers"] != ["target", "actual", "cumulative", "unavailable"]:
        errors.append("LAYER_COVERAGE")
    if (record["record_kind"] != "TEMPLATE_NOT_OBSERVED"
        or any(v is not None for v in record["timeline_ns"].values())
        or list(record["timeline_ns"]) != TIMELINE
        or record["actual_training_seconds"] is not None
        or record["mastery_time_seconds"] is not None
        or record["mastery_time_reason"] != "NOT_MEASURED"
        or record["training_contract_id"] != contract["contract_id"]):
        errors.append("TEMPLATE_PRESENTS_OBSERVATION")
    return errors


def main():
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))
    errors = validate(read(HERE / "contract.json"), read(BREATH),
                      read(HERE / "observation.template.json"))
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: teaching candidate consistency; real observations and research freeze remain pending")


if __name__ == "__main__":
    main()
