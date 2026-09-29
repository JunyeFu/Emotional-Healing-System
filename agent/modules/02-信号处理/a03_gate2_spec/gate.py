"""Ordered Gate 2 decision semantics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class GateResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUABLE = "NOT_EVALUABLE"


@dataclass(frozen=True)
class GateEvidence:
    applicability: GateResult
    scci_direction: GateResult
    comprehension_total: GateResult
    comprehension_critical_layers: GateResult
    effort: GateResult
    stage_error: GateResult


ORDERED_COMPONENTS = (
    "applicability",
    "scci_direction",
    "comprehension_total",
    "comprehension_critical_layers",
    "effort",
    "stage_error",
)

SYNTHETIC_RECEIPT_KEYS = {"evidence_class", "status", "config_sha256"}


def validate_synthetic_fixture_receipt(receipt: Mapping[str, object] | None) -> bool:
    if receipt is None or set(receipt) != SYNTHETIC_RECEIPT_KEYS:
        return False
    return (
        receipt.get("evidence_class") == "SYNTHETIC_ONLY"
        and receipt.get("status") == "FIXTURE"
        and isinstance(receipt.get("config_sha256"), str)
        and re.fullmatch(r"[A-Fa-f0-9]{64}", str(receipt["config_sha256"])) is not None
    )


def evaluate_ordered_gate(
    evidence: GateEvidence,
    *,
    evaluation_mode: str = "formal",
    fixture_receipt: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Evaluate without allowing a later component to compensate an earlier one."""
    if evaluation_mode == "formal":
        return {
            "result": GateResult.NOT_EVALUABLE.value,
            "stopped_at": "formal_parameters",
            "reason_code": "A03_CAL_NOT_DONE",
        }
    if evaluation_mode != "synthetic_fixture":
        raise ValueError("INVALID_EVALUATION_MODE")
    if not validate_synthetic_fixture_receipt(fixture_receipt):
        return {
            "result": GateResult.NOT_EVALUABLE.value,
            "stopped_at": "fixture_receipt",
            "reason_code": "SYNTHETIC_FIXTURE_RECEIPT_INVALID",
        }
    for component in ORDERED_COMPONENTS:
        result = getattr(evidence, component)
        if result != GateResult.PASS:
            return {
                "result": result.value,
                "stopped_at": component,
                "reason_code": (
                    f"{component.upper()}_FAILED"
                    if result == GateResult.FAIL
                    else f"{component.upper()}_NOT_EVALUABLE"
                ),
            }
    return {
        "result": GateResult.PASS.value,
        "stopped_at": None,
        "reason_code": "SYNTHETIC_ALL_ORDERED_COMPONENTS_PASS",
    }
