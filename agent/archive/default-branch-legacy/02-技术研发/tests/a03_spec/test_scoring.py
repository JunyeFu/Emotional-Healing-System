from __future__ import annotations

import pytest

from a03_gate2_spec import (
    ItemResponse,
    ResponseStatus,
    benjamini_hochberg,
    score_comprehension,
    score_effort,
    score_panas,
    score_scci,
    summarize_stage_errors,
)


def test_scci_is_labeled_as_manipulation_check_only():
    rows = [ItemResponse(f"S{i}", ResponseStatus.RESPONDED, i) for i in range(1, 5)]
    result = score_scci(rows)
    assert result["construct_role"] == "MANIPULATION_CHECK_ONLY"
    assert result["responded_mean"] == 2.5


def test_technical_unpresented_is_not_scored_as_wrong():
    layers = ["target", "actual", "cumulative", "degraded"]
    rows = []
    for layer in layers:
        rows.extend(
            [
                ItemResponse(f"{layer}-1", ResponseStatus.RESPONDED, 1, layer),
                ItemResponse(f"{layer}-2", ResponseStatus.RESPONDED, 1, layer),
            ]
        )
    rows[-1] = ItemResponse("degraded-2", ResponseStatus.TECH_UNPRESENTED, None, "degraded")
    result = score_comprehension(rows, nonresponse_policy="incorrect")
    assert result["correct"] == 7
    assert result["denominator"] == 7
    assert result["status_counts"]["TECH_UNPRESENTED"] == 1


def test_nonresponse_policy_is_explicit_and_changes_denominator():
    layers = ["target", "actual", "cumulative", "degraded"]
    rows = []
    for layer in layers:
        rows.extend(
            [
                ItemResponse(f"{layer}-1", ResponseStatus.RESPONDED, 1, layer),
                ItemResponse(f"{layer}-2", ResponseStatus.SKIPPED, None, layer),
            ]
        )
    assert score_comprehension(rows, nonresponse_policy="incorrect")["denominator"] == 8
    assert score_comprehension(rows, nonresponse_policy="exclude")["denominator"] == 4
    with pytest.raises(ValueError, match="NONRESPONSE_POLICY_NOT_FROZEN"):
        score_comprehension(rows, nonresponse_policy="default")


def test_effort_has_lower_is_less_direction():
    result = score_effort(ItemResponse("M1", ResponseStatus.RESPONDED, 4))
    assert result == {"value": 4.0, "direction": "LOWER_IS_LESS_EFFORT", "status": "RESPONDED"}


def test_panas_requires_frozen_item_mapping_and_keeps_dimensions_separate():
    rows = [
        ItemResponse("P1", ResponseStatus.RESPONDED, 4),
        ItemResponse("P2", ResponseStatus.RESPONDED, 3),
        ItemResponse("N1", ResponseStatus.RESPONDED, 2),
        ItemResponse("N2", ResponseStatus.RESPONDED, 1),
    ]
    with pytest.raises(ValueError, match="PANAS_FORMAL_SCORING_REQUIRES_A03_CAL"):
        score_panas(
            rows,
            positive_item_ids=["P1", "P2"],
            negative_item_ids=["N1", "N2"],
        )
    result = score_panas(
        rows,
        positive_item_ids=["P1", "P2"],
        negative_item_ids=["N1", "N2"],
        evaluation_mode="synthetic_fixture",
        fixture_receipt={
            "evidence_class": "SYNTHETIC_ONLY",
            "status": "FIXTURE",
            "config_sha256": "A" * 64,
        },
    )
    assert result["dimensions"]["positive"]["sum"] == 7
    assert result["dimensions"]["negative"]["sum"] == 3
    assert result["combined_total"] is None


def test_panas_rejects_string_or_malformed_fixture_receipts():
    rows = [
        ItemResponse("P1", ResponseStatus.RESPONDED, 4),
        ItemResponse("N1", ResponseStatus.RESPONDED, 2),
    ]
    with pytest.raises(ValueError, match="SYNTHETIC_FIXTURE_RECEIPT_INVALID"):
        score_panas(
            rows,
            positive_item_ids=["P1"],
            negative_item_ids=["N1"],
            evaluation_mode="synthetic_fixture",
            fixture_receipt={"evidence_class": "SYNTHETIC_ONLY"},
        )


def test_benjamini_hochberg_controls_item_family():
    decisions = benjamini_hochberg({"S1": 0.001, "S2": 0.02, "S3": 0.20, "S4": 0.80})
    assert decisions == {"S1": True, "S2": True, "S3": False, "S4": False}


def test_stage_errors_are_aggregated_against_observed_opportunities():
    result = summarize_stage_errors(
        [
            {"condition": "scene_native", "module": "storm", "error_count": 1, "opportunity_count": 8},
            {"condition": "scene_native", "module": "storm", "error_count": 2, "opportunity_count": 8},
            {"condition": "abstract_pacer", "module": "storm", "error_count": 0, "opportunity_count": 0},
        ]
    )
    assert result[1]["error_count"] == 3
    assert result[1]["error_rate"] == 3 / 16
    assert result[0]["reason_code"] == "NO_OBSERVABLE_OPPORTUNITY"
