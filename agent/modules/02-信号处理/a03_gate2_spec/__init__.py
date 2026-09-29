"""Executable A-03-SPEC scoring and synthetic feasibility helpers."""

from .gate import (
    GateEvidence,
    GateResult,
    evaluate_ordered_gate,
    validate_synthetic_fixture_receipt,
)
from .scoring import (
    ItemResponse,
    ResponseStatus,
    benjamini_hochberg,
    score_comprehension,
    score_effort,
    score_panas,
    score_scci,
    summarize_stage_errors,
)

__all__ = [
    "GateEvidence",
    "GateResult",
    "ItemResponse",
    "ResponseStatus",
    "benjamini_hochberg",
    "evaluate_ordered_gate",
    "score_comprehension",
    "score_effort",
    "score_panas",
    "score_scci",
    "summarize_stage_errors",
    "validate_synthetic_fixture_receipt",
]
