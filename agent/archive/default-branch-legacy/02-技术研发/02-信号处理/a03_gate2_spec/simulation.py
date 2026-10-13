"""Deterministic bounded Monte Carlo for A-03-SPEC sensitivity checks."""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, variance


ANALYSIS_SETS = ("PRIMARY_CONSERVATIVE", "OBSERVED_CASE")
COMPONENTS = (
    "scci",
    "comprehension",
    "critical_layers",
    "effort",
    "stage_error",
    "joint",
)


@dataclass(frozen=True)
class Scenario:
    name: str
    scci_shift: float
    comprehension_native: float
    comprehension_abstract: float
    effort_native: float
    effort_abstract: float
    stage_error_native: float
    stage_error_abstract: float
    skipped_rate: float = 0.02
    timeout_rate: float = 0.01
    technical_rate: float = 0.01
    native_missing_multiplier: float = 1.0


SCENARIOS = (
    Scenario("target", 0.75, 0.82, 0.84, 4.2, 4.0, 0.08, 0.07),
    Scenario("null_manipulation", 0.00, 0.82, 0.84, 4.2, 4.0, 0.08, 0.07),
    Scenario("ceiling", 0.65, 0.94, 0.95, 3.0, 2.9, 0.03, 0.03),
    Scenario(
        "differential_missing",
        0.75,
        0.80,
        0.84,
        4.5,
        4.0,
        0.10,
        0.07,
        skipped_rate=0.12,
        timeout_rate=0.05,
        technical_rate=0.05,
        native_missing_multiplier=1.5,
    ),
    Scenario("item_shift", 0.40, 0.82, 0.84, 4.2, 4.0, 0.08, 0.07),
)

SYNTHETIC_THRESHOLDS = {
    "scci_min_difference": 0.35,
    "comprehension_min_difference": -0.75,
    "critical_layer_min_difference": -1.25,
    "effort_max_difference": 1.00,
    "stage_error_max_difference": 0.08,
}


def _bounded_round(value: float, low: int, high: int) -> int:
    return min(high, max(low, int(round(value))))


def _bounded_beta(
    rng: random.Random, center: float, low: int, high: int, concentration: float
) -> int:
    proportion = min(0.99, max(0.01, (center - low) / (high - low)))
    value = low + (high - low) * rng.betavariate(
        proportion * concentration, (1 - proportion) * concentration
    )
    return _bounded_round(value, low, high)


def _response_status(rng: random.Random, scenario: Scenario, native: bool) -> str:
    multiplier = scenario.native_missing_multiplier if native else 1.0
    draw = rng.random()
    technical_boundary = scenario.technical_rate * multiplier
    timeout_boundary = technical_boundary + scenario.timeout_rate * multiplier
    skipped_boundary = timeout_boundary + scenario.skipped_rate * multiplier
    if draw < technical_boundary:
        return "TECH_UNPRESENTED"
    if draw < timeout_boundary:
        return "TIMEOUT"
    if draw < skipped_boundary:
        return "SKIPPED"
    return "RESPONDED"


def _participant(rng: random.Random, scenario: Scenario, native: bool) -> dict[str, object]:
    base_scci = 3.0 + (scenario.scci_shift if native else 0.0)
    scci_values = [_bounded_beta(rng, base_scci, 1, 5, 8.0) for _ in range(4)]
    if scenario.name == "item_shift" and native:
        scci_values[-1] = _bounded_round(scci_values[-1] - 1.0, 1, 5)
    scci_statuses = [_response_status(rng, scenario, native) for _ in range(4)]
    scci = [
        value if status == "RESPONDED" else None
        for value, status in zip(scci_values, scci_statuses, strict=True)
    ]

    probability = scenario.comprehension_native if native else scenario.comprehension_abstract
    comprehension: list[int | None] = []
    comprehension_statuses: list[str] = []
    for _ in range(8):
        status = _response_status(rng, scenario, native)
        comprehension_statuses.append(status)
        comprehension.append(int(rng.random() < probability) if status == "RESPONDED" else None)

    effort_status = _response_status(rng, scenario, native)
    effort_center = scenario.effort_native if native else scenario.effort_abstract
    effort = (
        _bounded_beta(rng, effort_center, 1, 9, 10.0)
        if effort_status == "RESPONDED"
        else None
    )

    stage_error_status = _response_status(rng, scenario, native)
    stage_probability = scenario.stage_error_native if native else scenario.stage_error_abstract
    stage_errors = (
        sum(rng.random() < stage_probability for _ in range(16)) / 16
        if stage_error_status == "RESPONDED"
        else None
    )
    return {
        "scci": scci,
        "scci_statuses": scci_statuses,
        "comprehension": comprehension,
        "comprehension_statuses": comprehension_statuses,
        "effort": effort,
        "effort_status": effort_status,
        "stage_errors": stage_errors,
        "stage_error_status": stage_error_status,
    }


def _analysis_value(
    value: float | int | None,
    status: str,
    analysis_set: str,
    conservative_value: float,
) -> float:
    if status == "RESPONDED":
        return float(value) if value is not None else math.nan
    if status == "TECH_UNPRESENTED" or analysis_set == "OBSERVED_CASE":
        return math.nan
    return conservative_value


def _scci_score(row: dict[str, object], analysis_set: str) -> float:
    values = row["scci"]
    statuses = row["scci_statuses"]
    assert isinstance(values, list) and isinstance(statuses, list)
    scored = [
        _analysis_value(value, status, analysis_set, 1.0)
        for value, status in zip(values, statuses, strict=True)
    ]
    kept = [value for value in scored if not math.isnan(value)]
    return mean(kept) if kept else math.nan


def _comprehension_score(row: dict[str, object], analysis_set: str) -> float:
    values = row["comprehension"]
    statuses = row["comprehension_statuses"]
    assert isinstance(values, list) and isinstance(statuses, list)
    scored = [
        _analysis_value(value, status, analysis_set, 0.0)
        for value, status in zip(values, statuses, strict=True)
    ]
    kept = [value for value in scored if not math.isnan(value)]
    return 8 * mean(kept) if kept else math.nan


def _layer_scores(row: dict[str, object], analysis_set: str) -> list[float]:
    values = row["comprehension"]
    statuses = row["comprehension_statuses"]
    assert isinstance(values, list) and isinstance(statuses, list)
    scores = []
    for start in range(0, 8, 2):
        layer = {
            "comprehension": values[start:start + 2],
            "comprehension_statuses": statuses[start:start + 2],
        }
        score = _comprehension_score(layer, analysis_set)
        scores.append(score / 4 if not math.isnan(score) else math.nan)
    return scores


def _contrast(rows: list[dict[str, object]], field: str) -> tuple[float, float]:
    native = [float(row[field]) for row in rows if row["condition"] == "scene_native"]
    abstract = [float(row[field]) for row in rows if row["condition"] == "abstract_pacer"]
    if len(native) < 2 or len(abstract) < 2:
        return math.nan, math.nan
    difference = mean(native) - mean(abstract)
    standard_error = math.sqrt(variance(native) / len(native) + variance(abstract) / len(abstract))
    return difference, standard_error


def _generate_experiment(
    rng: random.Random, scenario: Scenario, per_condition: int
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for native in (False, True):
        for _ in range(per_condition):
            row = _participant(rng, scenario, native)
            row["condition"] = "scene_native" if native else "abstract_pacer"
            rows.append(row)
    return rows


def _evaluate_experiment(
    source_rows: list[dict[str, object]], analysis_set: str
) -> dict[str, bool]:
    rows: list[dict[str, object]] = []
    for source in source_rows:
        row = dict(source)
        row["scci_score"] = _scci_score(source, analysis_set)
        row["comprehension_score"] = _comprehension_score(source, analysis_set)
        row["effort_score"] = _analysis_value(
            source["effort"], str(source["effort_status"]), analysis_set, 9.0
        )
        row["stage_error_score"] = _analysis_value(
            source["stage_errors"],
            str(source["stage_error_status"]),
            analysis_set,
            1.0,
        )
        for index, layer_score in enumerate(_layer_scores(source, analysis_set)):
            row[f"layer_{index}"] = layer_score
        rows.append(row)

    def rows_for(field: str) -> list[dict[str, object]]:
        return [row for row in rows if not math.isnan(float(row[field]))]

    z95 = 1.96
    scci_difference, scci_se = _contrast(rows_for("scci_score"), "scci_score")
    comprehension_difference, comprehension_se = _contrast(
        rows_for("comprehension_score"), "comprehension_score"
    )
    effort_difference, effort_se = _contrast(rows_for("effort_score"), "effort_score")
    stage_difference, stage_se = _contrast(
        rows_for("stage_error_score"), "stage_error_score"
    )
    layer_contrasts = [
        _contrast(rows_for(f"layer_{index}"), f"layer_{index}")
        for index in range(4)
    ]
    checks = {
        "scci": scci_difference - z95 * scci_se >= SYNTHETIC_THRESHOLDS["scci_min_difference"],
        "comprehension": comprehension_difference - z95 * comprehension_se >= SYNTHETIC_THRESHOLDS["comprehension_min_difference"],
        "critical_layers": all(
            difference - z95 * standard_error >= SYNTHETIC_THRESHOLDS["critical_layer_min_difference"]
            for difference, standard_error in layer_contrasts
        ),
        "effort": effort_difference + z95 * effort_se <= SYNTHETIC_THRESHOLDS["effort_max_difference"],
        "stage_error": stage_difference + z95 * stage_se <= SYNTHETIC_THRESHOLDS["stage_error_max_difference"],
    }
    checks["joint"] = all(checks.values())
    return checks


def run_simulation(
    *,
    seed: int = 20260906,
    replications: int = 1000,
    per_condition: int = 24,
    decision_scope: str = "sensitivity_point",
) -> dict[str, object]:
    if replications < 100 or per_condition < 2:
        raise ValueError("SIMULATION_BUDGET_TOO_SMALL")
    if decision_scope not in {
        "sensitivity_point", "existing_planning_anchor", "complete_target"
    }:
        raise ValueError("INVALID_DECISION_SCOPE")

    rng = random.Random(seed)
    results: dict[str, object] = {}
    for scenario in SCENARIOS:
        counts_by_set = {
            analysis_set: {name: 0 for name in COMPONENTS}
            for analysis_set in ANALYSIS_SETS
        }
        both_sets_joint = 0
        for _ in range(replications):
            source_rows = _generate_experiment(rng, scenario, per_condition)
            checks_by_set = {
                analysis_set: _evaluate_experiment(source_rows, analysis_set)
                for analysis_set in ANALYSIS_SETS
            }
            for analysis_set, checks in checks_by_set.items():
                for name, passed in checks.items():
                    counts_by_set[analysis_set][name] += int(passed)
            both_sets_joint += int(
                all(checks_by_set[analysis_set]["joint"] for analysis_set in ANALYSIS_SETS)
            )

        scenario_result: dict[str, object] = {}
        for analysis_set in ANALYSIS_SETS:
            probabilities = {
                name: count / replications
                for name, count in counts_by_set[analysis_set].items()
            }
            scenario_result[analysis_set] = {
                "pass_probability": probabilities,
                "joint_mc_standard_error": math.sqrt(
                    probabilities["joint"] * (1 - probabilities["joint"]) / replications
                ),
            }
        both_probability = both_sets_joint / replications
        scenario_result["BOTH_ANALYSIS_SETS"] = {
            "joint_pass_probability": both_probability,
            "joint_mc_standard_error": math.sqrt(
                both_probability * (1 - both_probability) / replications
            ),
        }
        results[scenario.name] = scenario_result

    target_joint = results["target"]["BOTH_ANALYSIS_SETS"]["joint_pass_probability"]
    null_joint = results["null_manipulation"]["BOTH_ANALYSIS_SETS"]["joint_pass_probability"]
    decision_prefix = {
        "sensitivity_point": "SYNTHETIC_SENSITIVITY_POINT",
        "existing_planning_anchor": "SYNTHETIC_EXISTING_PLANNING_ANCHOR",
        "complete_target": "SYNTHETIC_COMPLETE_TARGET",
    }[decision_scope]
    decision = f"{decision_prefix}_{'FEASIBLE' if target_joint >= 0.80 and null_joint <= 0.20 else 'NO_GO'}"
    return {
        "schema_version": "1.1",
        "evidence_class": "SYNTHETIC_ONLY",
        "seed": seed,
        "replications": replications,
        "decision_scope": decision_scope,
        "participants_per_condition": per_condition,
        "total_participants_per_replication": 2 * per_condition,
        "planning_anchor_source": (
            "CONTROL_BASELINE_GATE1_85_COMPLETE_FOUR_MODULE_RESULTS_PER_GROUP"
            if per_condition == 85
            else (
                "CONTROL_BASELINE_BALANCED_COMPLETE_TARGET_96_PER_GROUP"
                if per_condition == 96
                else "CALLER_SUPPLIED_SYNTHETIC_SENSITIVITY_VALUE"
            )
        ),
        "formal_margins": None,
        "formal_sample_size": None,
        "synthetic_sensitivity_thresholds": SYNTHETIC_THRESHOLDS,
        "scenarios": results,
        "decision": decision,
        "limitations": [
            "SYNTHETIC_PARAMETERS_ARE_NOT_REAL_CALIBRATION",
            "LEVEL_A_B_AND_C_EVIDENCE_NOT_PRESENT",
            "FORMAL_MARGINS_AND_SAMPLE_SIZE_NOT_FROZEN",
            "RECRUITMENT_CAP_240_NOT_MODELED_AS_COMPLETE_OUTCOMES",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--replications", type=int, default=1000)
    parser.add_argument("--per-condition", type=int, default=24)
    parser.add_argument(
        "--decision-scope",
        choices=("sensitivity_point", "existing_planning_anchor", "complete_target"),
        default="sensitivity_point",
    )
    args = parser.parse_args()
    report = run_simulation(
        seed=args.seed,
        replications=args.replications,
        per_condition=args.per_condition,
        decision_scope=args.decision_scope,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['decision']}: {args.output}")


if __name__ == "__main__":
    main()
