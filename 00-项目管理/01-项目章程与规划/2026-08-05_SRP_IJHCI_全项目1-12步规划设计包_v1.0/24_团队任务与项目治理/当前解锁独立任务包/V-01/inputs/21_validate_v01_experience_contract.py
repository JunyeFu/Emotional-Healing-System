"""Validate V-01 deliverables against the live protocol authority."""

from __future__ import annotations

import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
V01 = ROOT / "20_产品与场景设计" / "V-01_研究体验契约与完整旅程"
CONTRACT = V01 / "v01-experience-contract-v1.0.json"
PROTOCOL_AUTHORITY = ROOT / "00_总控" / "protocol_authority_v1.1.json"
FILES = (
    V01 / "README.md",
    V01 / "01_冻结项与开放项矩阵_v1.0.md",
    V01 / "02_目标体验简报_v1.0.md",
    V01 / "03_完整参与者旅程_v1.0.md",
    V01 / "04_MDA反推与主张追踪表_v1.0.md",
    V01 / "05_场景设计决策日志_v1.0.md",
    CONTRACT,
    PROTOCOL_AUTHORITY,
)
MODULES = ["storm", "heat", "snow", "fade"]
SEGMENTS = ["demo", "closed_loop", "lock_transition"]
LAYERS = ["target", "actual", "cumulative", "fallback"]
CLAIM_META = {
    "C-001": ("RESEARCH_VARIABLE", "DESIGN_HYPOTHESIS_NOT_OBSERVED"),
    "C-002": ("RESEARCH_VARIABLE", "DESIGN_HYPOTHESIS_NOT_OBSERVED"),
    "C-003": ("RESEARCH_VARIABLE", "DESIGN_HYPOTHESIS_NOT_OBSERVED"),
    "C-004": ("RUNTIME_EVIDENCE", "ENGINEERING_CANDIDATE"),
    "C-005": ("RUNTIME_EVIDENCE", "ENGINEERING_CANDIDATE"),
    "C-006": ("RESEARCH_VARIABLE", "DESIGN_HYPOTHESIS_NOT_OBSERVED"),
    "C-007": ("RESEARCH_VARIABLE", "OUT_OF_SCOPE"),
    "C-008": ("RESEARCH_VARIABLE", "CONDITIONAL_STAGE_3"),
    "C-009": ("NON_RESEARCH_DECORATION", "OUT_OF_SCOPE"),
    "C-010": ("RESEARCH_VARIABLE", "DESIGN_HYPOTHESIS_NOT_OBSERVED"),
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def validate_authority_alignment(contract: dict, protocol: dict, errors: list[str]) -> None:
    design = contract.get("research_design", {})
    authority_core = protocol.get("core_experience", {})
    participant_rule = protocol.get("participant_rule", {})

    require(protocol.get("schema_version") == "1.1", "unexpected protocol authority version", errors)
    require(protocol.get("evidence_status") == "PLANNED_NOT_OBSERVED", "protocol evidence status drifted", errors)
    require(design.get("stage_1_conditions") == protocol.get("stages", {}).get("stage_1", {}).get("cue_modes"), "stage 1 modes differ from authority", errors)
    require(design.get("participant_runs") == int(participant_rule.get("one_core_experience") is True), "participant core count differs from authority", errors)
    require(design.get("participant_stages") == int(participant_rule.get("one_stage") is True), "participant stage count differs from authority", errors)
    require(design.get("participant_conditions") == int(participant_rule.get("one_condition") is True), "participant condition count differs from authority", errors)
    require(design.get("module_count") == authority_core.get("module_count"), "module count differs from authority", errors)

    timing = contract.get("timing", {})
    require(timing.get("default_seconds") == authority_core.get("segments_seconds"), "default timing differs from authority", errors)
    require(timing.get("allowed_seconds") == authority_core.get("technical_ranges_seconds"), "timing ranges differ from authority", errors)
    require(timing.get("default_core_seconds") == authority_core.get("recommended_total_seconds"), "core duration differs from authority", errors)

    runtime = contract.get("formal_runtime_requirements", {})
    authority_runtime = protocol.get("formal_runtime", {})
    runtime_keys = (
        "python_is_authority",
        "unity_independent_of_td",
        "td_read_only",
        "spout_forbidden",
        "mock_forbidden",
        "live_e2e_required",
    )
    for key in runtime_keys:
        require(runtime.get(key) == authority_runtime.get(key), f"runtime rule {key} differs from authority", errors)

    boundaries = protocol.get("claim_boundaries", {})
    require(boundaries.get("stage_1_treatment") == design.get("condition_unit"), "stage 1 treatment differs from authority", errors)
    require(boundaries.get("stage_3_treatment") == design.get("stage_3", {}).get("treatment"), "stage 3 treatment differs from authority", errors)
    for key in (
        "whole_project_causal_effect",
        "independent_weather_effect",
        "independent_breathing_structure_effect",
        "single_visual_mechanism_effect",
    ):
        require(boundaries.get(key) is False, f"claim boundary {key} drifted", errors)


def validate_condition_packages(contract: dict, protocol: dict, errors: list[str]) -> None:
    design = contract.get("research_design", {})
    require(design.get("module_ids") == MODULES, "module IDs drifted", errors)
    require(design.get("module_count") == 4, "module_count must be 4", errors)
    require(design.get("module_occurrence") == "exactly_once", "modules must occur exactly once", errors)
    require(design.get("sequence_source") == "python_manifest", "sequence authority is not Python manifest", errors)
    require(design.get("participant_input_during_core") is False, "participant input enabled in core", errors)
    require(design.get("unity_reads_pre_measure") is False, "Unity must not read pre measure", errors)
    require(design.get("unity_reads_post_measure") is False, "Unity must not read post measure", errors)
    require(design.get("condition_unit") == "complete_cue_representation_package", "condition unit drifted", errors)

    packages = design.get("condition_packages", {})
    require(set(packages) == {"scene_native", "abstract_pacer"}, "condition packages incomplete", errors)
    for mode in ("scene_native", "abstract_pacer"):
        package = packages.get(mode, {})
        require(package.get("module_ids") == MODULES, f"{mode} does not cover all modules", errors)
        require(package.get("segments") == SEGMENTS, f"{mode} does not cover all segments", errors)
        require(package.get("truth_layers") == LAYERS, f"{mode} truth layers incomplete", errors)
        require(package.get("timing_profile") == "shared", f"{mode} timing is not shared", errors)
        require(package.get("audio_semantics") == "shared", f"{mode} audio semantics are not shared", errors)

    stage_3 = design.get("stage_3", {})
    authority_stage_3 = protocol.get("stages", {}).get("stage_3", {})
    require(stage_3.get("arms") == authority_stage_3.get("arms"), "stage 3 arms drifted", errors)
    require(stage_3.get("cue_mode") == "scene_native", "stage 3 cue mode drifted", errors)
    require(stage_3.get("same_unity_build") == authority_stage_3.get("same_scene_native_build"), "stage 3 build rule drifted", errors)
    require(stage_3.get("sequence_source") == "python_policy_or_manifest", "stage 3 sequence authority drifted", errors)


def validate_roles_and_timing(contract: dict, errors: list[str]) -> None:
    roles = contract.get("roles", {})
    python_roles = set(roles.get("python", []))
    unity_roles = set(roles.get("unity", []))
    td_roles = set(roles.get("touchdesigner", []))
    require({"session_authority", "sequence_authority", "clock_authority", "interaction_state_estimation"} <= python_roles, "Python authority incomplete", errors)
    require("participant_product" in unity_roles and "render_state_mirror" in unity_roles, "Unity role incomplete", errors)
    forbidden_authority = {"session_authority", "sequence_authority", "clock_authority", "control_authority"}
    require(not unity_roles.intersection(forbidden_authority), "Unity owns forbidden authority", errors)
    require(td_roles == {"read_only_console", "data_monitoring"}, "TouchDesigner role drifted", errors)
    require(not td_roles.intersection(forbidden_authority), "TouchDesigner owns forbidden authority", errors)
    require(roles.get("spout_used") is False, "Spout must not be used", errors)

    timing = contract.get("timing", {})
    defaults = timing.get("default_seconds", {})
    require(timing.get("segments") == SEGMENTS, "segment order drifted", errors)
    require(defaults == {"demo": 25, "closed_loop": 150, "lock_transition": 25}, "default timing drifted", errors)
    require(sum(defaults.values()) == timing.get("default_module_seconds"), "module duration sum mismatch", errors)
    require(timing.get("default_module_seconds", 0) * 4 == timing.get("default_core_seconds"), "core duration sum mismatch", errors)


def validate_journey_and_claims(contract: dict, documents: str, errors: list[str]) -> None:
    representation = contract.get("representation", {})
    require(representation.get("truth_layers") == LAYERS, "truth layers drifted", errors)
    require(representation.get("same_truth_across_conditions") is True, "condition truth is not shared", errors)
    require(representation.get("same_audio_semantics_across_conditions") is True, "audio semantics are not shared", errors)
    require(representation.get("abstract_form_frozen") is False, "abstract form was prematurely frozen", errors)

    journey = contract.get("journey", [])
    require([item.get("id") for item in journey] == [f"J-{index:02d}" for index in range(1, 13)], "journey IDs/order drifted", errors)
    for item in journey:
        if item.get("surface") in {"unity", "unity_core"}:
            require(item.get("participant_action") == "none", f"Unity journey {item.get('id')} requires participant action", errors)
    require(contract.get("non_timed_journey_boundaries") == ["J-05", "J-09"], "non-timed journey boundaries drifted", errors)

    frozen = contract.get("frozen_ids", [])
    versioned = contract.get("versioned_change_ids", [])
    opened = contract.get("open_ids", [])
    all_boundary_ids = frozen + versioned + opened
    require(len(all_boundary_ids) == len(set(all_boundary_ids)), "duplicate boundary ID", errors)
    require(set(frozen + versioned) == {f"F-{index:03d}" for index in range(1, 27)}, "frozen/versioned boundary set incomplete", errors)
    require(set(opened) == {f"O-{index:03d}" for index in range(1, 16)}, "open boundary set incomplete", errors)
    require(set(re.findall(r"\bF-\d{3}\b", documents)) >= set(frozen + versioned), "documented frozen IDs incomplete", errors)
    require(set(re.findall(r"\bO-\d{3}\b", documents)) >= set(opened), "documented open IDs incomplete", errors)

    claims = contract.get("claims", [])
    required_claim_ids = contract.get("required_claim_ids", [])
    require([item.get("id") for item in claims] == required_claim_ids, "structured claims missing or out of order", errors)
    require(required_claim_ids == list(CLAIM_META), "required claim IDs drifted", errors)
    claim_rows = {
        match.group("id"): (match.group("classification"), match.group("status"))
        for match in re.finditer(
            r"\| (?P<id>C-\d{3}) \|[^\n]*?\| (?P<classification>RESEARCH_VARIABLE|RUNTIME_EVIDENCE|NON_RESEARCH_DECORATION) \|[^\n]*?\|[^\n]*?\| (?P<status>[A-Z0-9_]+) \|",
            documents,
        )
    }
    for claim in claims:
        claim_id = claim.get("id")
        expected = CLAIM_META.get(claim_id)
        require(expected is not None, f"unexpected claim {claim_id}", errors)
        if expected is not None:
            require((claim.get("classification"), claim.get("status")) == expected, f"claim {claim_id} metadata drifted", errors)
            require(claim_rows.get(claim_id) == expected, f"claim {claim_id} markdown metadata drifted", errors)
        require(bool(claim.get("evidence_refs")), f"claim {claim_id} has no evidence refs", errors)
        require(bool(claim.get("conclusion_boundary")), f"claim {claim_id} has no conclusion boundary", errors)


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        if not path.is_file():
            errors.append(f"missing file: {path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    documents = "\n".join(path.read_text(encoding="utf-8-sig") for path in FILES[:6])
    try:
        contract = load_json(CONTRACT)
        protocol = load_json(PROTOCOL_AUTHORITY)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: authority JSON: {exc}")
        return 1

    require(contract.get("contract_id") == "SRP-V01-EXPERIENCE-CONTRACT", "wrong contract_id", errors)
    require(contract.get("version") == "1.0.0", "wrong contract version", errors)
    require(contract.get("status") == "CANDIDATE_FOR_REVIEW", "wrong contract status", errors)
    validate_authority_alignment(contract, protocol, errors)
    validate_condition_packages(contract, protocol, errors)
    validate_roles_and_timing(contract, errors)
    validate_journey_and_claims(contract, documents, errors)

    evidence = contract.get("evidence_state", {})
    require(evidence.get("participant_results") == "NOT_OBSERVED", "participant results overstated", errors)
    require(evidence.get("unity_build") == "NOT_PRODUCED_BY_V01", "Unity build evidence overstated", errors)
    for marker in (
        "第一模块只来自 manifest",
        "TouchDesigner 是只读操作台",
        "DESIGN_HYPOTHESIS_NOT_OBSERVED",
        "未形成可发布 Unity 构建",
    ):
        require(marker in documents, f"missing design marker: {marker}", errors)
    require(not re.search(r"turn\d+(?:file|search|view)", documents, flags=re.IGNORECASE), "internal citation found", errors)
    require("sandbox:/" not in documents, "sandbox link found", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "PASS: V-01 contract aligned to protocol v1.1; 26 frozen/versioned constraints; "
        "15 open decisions; 12 journey nodes; 10 structured claims"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
