"""U12-04 contract validation: PANAS primary SAP vs protocol authority.

validate(contract, protocol, record) returns a list of error codes; empty
list means the candidate contract is internally consistent and aligned with
the authoritative protocol_authority_v1.2.json contract.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
# protocol authority lives in the same v1.0 package root as this deliverable.
PACKAGE_ROOT = HERE.parents[2]
PROTOCOL = PACKAGE_ROOT / "00_总控" / "protocol_authority_v1.2.json"
# task registry lives in the sibling v1.2 package (same 01-项目章程与规划 parent).
REGISTRY_ROOT = HERE.parents[3] / "2026-09-08_SRP_v1.2_当前基线适配包" / "tasks" / "U12-04"

REQUIRED_FREEZES = (
    "panas_version_and_permission",
    "eligibility_and_recruitment",
    "training_budget",
    "randomization_and_concealment",
    "minimum_important_affect_difference",
    "missingness_and_mnar",
    "functional_margin_justification",
    "critical_error_thresholds",
    "final_power_and_n",
    "stopping_rule",
    "institutional_scope",
    "live_e2e",
    "runtime_gate_integration",
    "data_retention_and_access",
    "pretreatment_baseline_and_condition_training_order",
)

PRIMARY_FIELDS = (
    "stage",
    "outcome",
    "unit",
    "contrast",
    "native_code",
    "abstract_code",
    "lower_is_better",
    "candidate_model",
    "candidate_variance",
    "test",
    "alpha",
    "ci_level",
    "post_treatment_covariates_in_primary_model",
    "pretreatment_baseline_required",
    "report_even_if_functional_guard_fails",
)

CLAIM_BOUNDARY_FIELDS = (
    "whole_project_causal_effect",
    "independent_weather_effect",
    "independent_breathing_structure_effect",
    "single_visual_mechanism_effect",
    "long_term_effect",
    "short_vs_long_interaction",
    "diagnosis_or_treatment_efficacy",
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(contract: dict, protocol: dict, record: dict) -> list[str]:
    errors: list[str] = []

    # --- freeze / collection gate -------------------------------------
    if contract.get("status") != "CANDIDATE_NOT_RESEARCH_FROZEN":
        errors.append("UNAPPROVED_FREEZE")
    if contract.get("formal_collection_allowed") is not False:
        errors.append("UNAPPROVED_FREEZE")
    if contract.get("research_freeze_required") is not True:
        errors.append("FREEZE_NOT_REQUIRED")

    # --- primary alignment ---------------------------------------------
    prot_primary = protocol.get("primary", {})
    con_primary = contract.get("primary", {})
    for field in PRIMARY_FIELDS:
        if field in prot_primary and con_primary.get(field) != prot_primary.get(field):
            errors.append("CONTRACT_MISMATCH_PRIMARY")

    # --- functional guard margin must stay justified (not frozen) ------
    if (
        contract.get("functional_guard", {}).get("margin_status")
        != "INHERITED_REQUIRES_JUSTIFICATION"
    ):
        errors.append("FUNCTIONAL_MARGIN_NOT_JUSTIFIED")

    # --- equivalence default disabled ----------------------------------
    if contract.get("equivalence", {}).get("confirmatory_enabled") is not False:
        errors.append("EQUIVALENCE_NOT_DISABLED")

    # --- nothing formal may be frozen in this candidate ----------------
    if contract.get("sample_planning", {}).get("formal_randomized_n") is not None:
        errors.append("N_FROZEN_PREMATURELY")
    if contract.get("sample_planning", {}).get("formal_recruitment_cap") is not None:
        errors.append("N_FROZEN_PREMATURELY")
    if contract.get("primary", {}).get("minimum_important_affect_difference") is not None:
        errors.append("MARGIN_FROZEN_PREMATURELY")
    if contract.get("equivalence", {}).get("margin") is not None:
        errors.append("MARGIN_FROZEN_PREMATURELY")

    # --- missingness must require SAP freeze ---------------------------
    if contract.get("missingness", {}).get("status") != "SAP_FREEZE_REQUIRED":
        errors.append("MISSINGNESS_NOT_REQUIRED")

    # --- power simulation consistency ----------------------------------
    power = contract.get("power_simulation", {})
    if power.get("alpha") != prot_primary.get("alpha"):
        errors.append("POWER_SPEC_MISMATCH")
    if power.get("test") != prot_primary.get("test"):
        errors.append("POWER_SPEC_MISMATCH")
    if power.get("variance") != prot_primary.get("candidate_variance"):
        errors.append("POWER_SPEC_MISMATCH")
    if power.get("target_power") != protocol.get("sample_planning", {}).get(
        "main_power_target_candidate"
    ):
        errors.append("POWER_SPEC_MISMATCH")
    if power.get("n_frozen") is not False or power.get("effect_frozen") is not False:
        errors.append("POWER_SPEC_FROZEN_PREMATURELY")

    # --- evidence class -------------------------------------------------
    if contract.get("evidence_class") != "DESIGN_AND_SYNTHETIC_ONLY":
        errors.append("EVIDENCE_CLASS_INVALID")
    if contract.get("evidence_status") != "DESIGN_AND_SYNTHETIC_ONLY":
        errors.append("EVIDENCE_CLASS_INVALID")

    # --- claim boundaries all false -------------------------------------
    for field in CLAIM_BOUNDARY_FIELDS:
        if contract.get("claim_boundaries", {}).get(field) is not False:
            errors.append("CLAIM_BOUNDARY_VIOLATION")

    # --- required freezes present ----------------------------------------
    freezes = contract.get("required_freezes", [])
    for name in REQUIRED_FREEZES:
        if name not in freezes:
            errors.append("REQUIRED_FREEZES_MISSING")

    # --- baseline commit ties to task input ------------------------------
    # task_input.json stores the field as "base_commit"; accept either key.
    record_baseline = None
    if record is not None:
        record_baseline = record.get("base_commit") or record.get("baseline_commit")
    if record is not None and record_baseline and contract.get("baseline_commit") != record_baseline:
        errors.append("BASELINE_COMMIT_MISMATCH")

    return errors


def main() -> None:
    read = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    contract = read(HERE / "contract.json")
    protocol = read(PROTOCOL)
    record_path = REGISTRY_ROOT / "inputs" / "task_input.json"
    record = read(record_path) if record_path.exists() else {}
    errors = validate(contract, protocol, record)
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: U12-04 contract aligned with protocol_authority_v1.2.json")


if __name__ == "__main__":
    main()
