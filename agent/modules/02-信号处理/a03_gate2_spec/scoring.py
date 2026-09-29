"""Pure scoring rules for the A-03-SPEC candidate instruments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence

from .gate import validate_synthetic_fixture_receipt


class ResponseStatus(str, Enum):
    RESPONDED = "RESPONDED"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"
    TECH_UNPRESENTED = "TECH_UNPRESENTED"


@dataclass(frozen=True)
class ItemResponse:
    item_id: str
    status: ResponseStatus
    value: float | int | None
    layer: str | None = None


def _status_counts(items: Sequence[ItemResponse]) -> dict[str, int]:
    return {
        status.value: sum(item.status == status for item in items)
        for status in ResponseStatus
    }


def _require_unique_ids(items: Sequence[ItemResponse]) -> None:
    ids = [item.item_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_ITEM_ID")


def score_scci(items: Sequence[ItemResponse]) -> dict[str, object]:
    """Score four ordinal SCCI items without imputing nonresponses."""
    _require_unique_ids(items)
    if len(items) != 4:
        raise ValueError("SCCI_REQUIRES_FOUR_ITEMS")
    values: list[float] = []
    for item in items:
        if item.status == ResponseStatus.RESPONDED:
            if item.value is None or not 1 <= float(item.value) <= 5:
                raise ValueError(f"SCCI_VALUE_OUT_OF_RANGE:{item.item_id}")
            values.append(float(item.value))
        elif item.value is not None:
            raise ValueError(f"NONRESPONSE_HAS_VALUE:{item.item_id}")
    return {
        "construct_role": "MANIPULATION_CHECK_ONLY",
        "responded_mean": sum(values) / len(values) if values else None,
        "responded_count": len(values),
        "status_counts": _status_counts(items),
    }


def score_panas(
    items: Sequence[ItemResponse],
    *,
    positive_item_ids: Sequence[str],
    negative_item_ids: Sequence[str],
    evaluation_mode: str = "formal",
    fixture_receipt: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Score configured dimensions for fixtures; formal scoring waits for A-03-CAL."""
    _require_unique_ids(items)
    if evaluation_mode == "formal":
        raise ValueError("PANAS_FORMAL_SCORING_REQUIRES_A03_CAL")
    if evaluation_mode != "synthetic_fixture":
        raise ValueError("INVALID_EVALUATION_MODE")
    if not validate_synthetic_fixture_receipt(fixture_receipt):
        raise ValueError("SYNTHETIC_FIXTURE_RECEIPT_INVALID")
    positive = set(positive_item_ids)
    negative = set(negative_item_ids)
    if not positive or not negative or positive & negative:
        raise ValueError("PANAS_DIMENSION_MAP_INVALID")
    if {item.item_id for item in items} != positive | negative:
        raise ValueError("PANAS_ITEM_SET_MISMATCH")

    dimensions: dict[str, object] = {}
    for name, expected_ids in (("positive", positive), ("negative", negative)):
        rows = [item for item in items if item.item_id in expected_ids]
        values: list[float] = []
        for item in rows:
            if item.status == ResponseStatus.RESPONDED:
                if item.value is None or not 1 <= float(item.value) <= 5:
                    raise ValueError(f"PANAS_VALUE_OUT_OF_RANGE:{item.item_id}")
                values.append(float(item.value))
            elif item.value is not None:
                raise ValueError(f"NONRESPONSE_HAS_VALUE:{item.item_id}")
        dimensions[name] = {
            "sum": sum(values) if len(values) == len(rows) else None,
            "complete": len(values) == len(rows),
            "status_counts": _status_counts(rows),
        }
    return {
        "dimensions": dimensions,
        "combined_total": None,
        "evidence_class": "SYNTHETIC_ONLY",
        "fixture_config_sha256": fixture_receipt["config_sha256"],
    }


def score_comprehension(
    items: Sequence[ItemResponse], *, nonresponse_policy: str
) -> dict[str, object]:
    """Score eight binary items across four layers.

    SKIPPED/TIMEOUT behavior must be explicit. TECH_UNPRESENTED is always
    excluded from the denominator and reported separately.
    """
    _require_unique_ids(items)
    if len(items) != 8:
        raise ValueError("COMPREHENSION_REQUIRES_EIGHT_ITEMS")
    if nonresponse_policy not in {"incorrect", "exclude"}:
        raise ValueError("NONRESPONSE_POLICY_NOT_FROZEN")

    expected_layers = {"target", "actual", "cumulative", "degraded"}
    layer_rows: dict[str, list[ItemResponse]] = {layer: [] for layer in expected_layers}
    for item in items:
        if item.layer not in expected_layers:
            raise ValueError(f"INVALID_COMPREHENSION_LAYER:{item.item_id}")
        layer_rows[item.layer].append(item)
    if any(len(rows) != 2 for rows in layer_rows.values()):
        raise ValueError("COMPREHENSION_REQUIRES_TWO_ITEMS_PER_LAYER")

    def score_rows(rows: Iterable[ItemResponse]) -> tuple[int, int]:
        correct = 0
        denominator = 0
        for item in rows:
            if item.status == ResponseStatus.TECH_UNPRESENTED:
                if item.value is not None:
                    raise ValueError(f"NONRESPONSE_HAS_VALUE:{item.item_id}")
                continue
            if item.status == ResponseStatus.RESPONDED:
                if item.value not in {0, 1}:
                    raise ValueError(f"COMPREHENSION_VALUE_NOT_BINARY:{item.item_id}")
                correct += int(item.value)
                denominator += 1
            else:
                if item.value is not None:
                    raise ValueError(f"NONRESPONSE_HAS_VALUE:{item.item_id}")
                if nonresponse_policy == "incorrect":
                    denominator += 1
        return correct, denominator

    total_correct, total_denominator = score_rows(items)
    layers = {}
    for layer, rows in sorted(layer_rows.items()):
        correct, denominator = score_rows(rows)
        layers[layer] = {"correct": correct, "denominator": denominator}
    return {
        "correct": total_correct,
        "denominator": total_denominator,
        "layers": layers,
        "nonresponse_policy": nonresponse_policy,
        "status_counts": _status_counts(items),
    }


def score_effort(item: ItemResponse) -> dict[str, object]:
    """Score the single 1-9 mental-effort item; lower is less effort."""
    if item.status == ResponseStatus.RESPONDED:
        if item.value is None or not 1 <= float(item.value) <= 9:
            raise ValueError("EFFORT_VALUE_OUT_OF_RANGE")
        value: float | None = float(item.value)
    else:
        if item.value is not None:
            raise ValueError("NONRESPONSE_HAS_VALUE")
        value = None
    return {
        "value": value,
        "direction": "LOWER_IS_LESS_EFFORT",
        "status": item.status.value,
    }


def benjamini_hochberg(p_values: Mapping[str, float], alpha: float = 0.05) -> dict[str, bool]:
    """Return Benjamini-Hochberg rejection decisions by item identifier."""
    if not 0 < alpha < 1:
        raise ValueError("INVALID_FDR_ALPHA")
    ordered = sorted(p_values.items(), key=lambda pair: (pair[1], pair[0]))
    if any(not 0 <= value <= 1 for _, value in ordered):
        raise ValueError("P_VALUE_OUT_OF_RANGE")
    cutoff_rank = 0
    total = len(ordered)
    for rank, (_, value) in enumerate(ordered, start=1):
        if value <= alpha * rank / total:
            cutoff_rank = rank
    rejected = {item_id for item_id, _ in ordered[:cutoff_rank]}
    return {item_id: item_id in rejected for item_id in p_values}


def summarize_stage_errors(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Aggregate objective stage errors by condition and module."""
    totals: dict[tuple[str, str], list[int]] = {}
    for record in records:
        condition = str(record.get("condition", ""))
        module = str(record.get("module", ""))
        errors = int(record.get("error_count", -1))
        opportunities = int(record.get("opportunity_count", -1))
        if not condition or not module:
            raise ValueError("STAGE_ERROR_GROUP_MISSING")
        if errors < 0 or opportunities < 0 or errors > opportunities:
            raise ValueError("STAGE_ERROR_COUNT_INVALID")
        bucket = totals.setdefault((condition, module), [0, 0])
        bucket[0] += errors
        bucket[1] += opportunities
    return [
        {
            "condition": condition,
            "module": module,
            "error_count": counts[0],
            "opportunity_count": counts[1],
            "error_rate": counts[0] / counts[1] if counts[1] else None,
            "reason_code": None if counts[1] else "NO_OBSERVABLE_OPPORTUNITY",
        }
        for (condition, module), counts in sorted(totals.items())
    ]
