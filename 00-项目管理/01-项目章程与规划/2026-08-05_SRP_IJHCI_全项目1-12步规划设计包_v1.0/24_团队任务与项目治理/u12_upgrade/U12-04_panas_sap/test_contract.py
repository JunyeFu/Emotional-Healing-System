"""U12-04 contract pytest: PANAS primary SAP alignment checks.

Covers: two-sided primary comparison, equivalence disabled by default,
N / margin unfrozen, missingness SAP-freeze required, functional margin
unjustified status, claim boundaries all false, required freezes present.
"""

from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
PACKAGE_ROOT = HERE.parents[2]
PROTOCOL = PACKAGE_ROOT / "00_总控" / "protocol_authority_v1.2.json"
REGISTRY_ROOT = HERE.parents[3] / "2026-09-08_SRP_v1.2_当前基线适配包" / "tasks" / "U12-04"

V = runpy.run_path(str(HERE / "validate.py"))


def inputs():
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    contract = read(HERE / "contract.json")
    protocol = read(PROTOCOL)
    record_path = REGISTRY_ROOT / "inputs" / "task_input.json"
    record = read(record_path) if record_path.exists() else {}
    return contract, protocol, record


def test_candidate():
    contract, protocol, record = inputs()
    assert V["validate"](contract, protocol, record) == []


@pytest.mark.parametrize(
    "key,value,code",
    [
        (("equivalence", "confirmatory_enabled"), True, "EQUIVALENCE_NOT_DISABLED"),
        (
            ("sample_planning", "formal_randomized_n"),
            192,
            "N_FROZEN_PREMATURELY",
        ),
        (
            ("sample_planning", "formal_recruitment_cap"),
            240,
            "N_FROZEN_PREMATURELY",
        ),
        (
            ("primary", "minimum_important_affect_difference"),
            0.15,
            "MARGIN_FROZEN_PREMATURELY",
        ),
        (("equivalence", "margin"), 0.1, "MARGIN_FROZEN_PREMATURELY"),
        (("primary", "test"), "one_sided", "CONTRACT_MISMATCH_PRIMARY"),
        (("primary", "candidate_variance"), "OLS", "CONTRACT_MISMATCH_PRIMARY"),
        (("primary", "alpha"), 0.01, "CONTRACT_MISMATCH_PRIMARY"),
        (("missingness", "status"), "FROZEN", "MISSINGNESS_NOT_REQUIRED"),
        (
            ("functional_guard", "margin_status"),
            "FROZEN",
            "FUNCTIONAL_MARGIN_NOT_JUSTIFIED",
        ),
        (
            ("claim_boundaries", "whole_project_causal_effect"),
            True,
            "CLAIM_BOUNDARY_VIOLATION",
        ),
        (
            ("power_simulation", "n_frozen"),
            True,
            "POWER_SPEC_FROZEN_PREMATURELY",
        ),
        (("status",), "RESEARCH_FROZEN", "UNAPPROVED_FREEZE"),
        (("formal_collection_allowed",), True, "UNAPPROVED_FREEZE"),
    ],
)
def test_mutations(key, value, code):
    contract, protocol, record = inputs()
    c = copy.deepcopy(contract)
    node = c
    for part in key[:-1]:
        node = node[part]
    node[key[-1]] = value
    assert code in V["validate"](c, protocol, record)


def test_two_sided_primary_kept():
    """Two-sided test must match the protocol; switching breaks alignment."""
    contract, protocol, record = inputs()
    c = copy.deepcopy(contract)
    c["primary"]["test"] = "two_sided"
    c["primary"]["alpha"] = 0.05
    assert V["validate"](c, protocol, record) == []


def test_negative_candidate_rejected():
    """Invalid evidence class must be rejected even if everything else passes."""
    contract, protocol, record = inputs()
    c = copy.deepcopy(contract)
    c["evidence_class"] = "REAL_CLIPS"
    c["evidence_status"] = "REAL_CLIPS"
    assert "EVIDENCE_CLASS_INVALID" in V["validate"](c, protocol, record)


def test_required_freezes_present():
    contract, protocol, record = inputs()
    c = copy.deepcopy(contract)
    c["required_freezes"] = []
    assert "REQUIRED_FREEZES_MISSING" in V["validate"](c, protocol, record)
