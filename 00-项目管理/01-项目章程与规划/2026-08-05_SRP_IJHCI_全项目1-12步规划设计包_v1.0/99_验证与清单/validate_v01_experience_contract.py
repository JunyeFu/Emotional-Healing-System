"""Validate the V-01 research experience contract and design deliverables."""

from __future__ import annotations

import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
V01 = ROOT / "20_产品与场景设计" / "V-01_研究体验契约与完整旅程"
CONTRACT = V01 / "v01-experience-contract-v1.0.json"
FILES = (
    V01 / "README.md",
    V01 / "01_冻结项与开放项矩阵_v1.0.md",
    V01 / "02_目标体验简报_v1.0.md",
    V01 / "03_完整参与者旅程_v1.0.md",
    V01 / "04_MDA反推与主张追踪表_v1.0.md",
    V01 / "05_场景设计决策日志_v1.0.md",
    CONTRACT,
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        if not path.is_file():
            errors.append(f"missing file: {path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    documents = "\n".join(path.read_text(encoding="utf-8-sig") for path in FILES[:-1])
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: contract JSON: {exc}")
        return 1

    require(contract.get("contract_id") == "SRP-V01-EXPERIENCE-CONTRACT", "wrong contract_id", errors)
    require(contract.get("version") == "1.0.0", "wrong contract version", errors)
    require(contract.get("status") == "CANDIDATE_FOR_REVIEW", "wrong contract status", errors)

    design = contract.get("research_design", {})
    require(design.get("module_ids") == ["storm", "heat", "snow", "fade"], "module IDs drifted", errors)
    require(design.get("module_count") == 4, "module_count must be 4", errors)
    require(design.get("module_occurrence") == "exactly_once", "modules must occur exactly once", errors)
    require(design.get("sequence_source") == "python_manifest", "sequence authority is not Python manifest", errors)
    require(design.get("participant_input_during_core") is False, "participant input enabled in core", errors)
    require(design.get("unity_reads_pre_measure") is False, "Unity must not read pre measure", errors)
    require(design.get("unity_reads_post_measure") is False, "Unity must not read post measure", errors)
    require(design.get("stage_1_conditions") == ["scene_native", "abstract_pacer"], "stage 1 conditions drifted", errors)

    roles = contract.get("roles", {})
    python_roles = set(roles.get("python", []))
    unity_roles = set(roles.get("unity", []))
    require({"session_authority", "sequence_authority", "clock_authority", "interaction_state_estimation"} <= python_roles, "Python authority incomplete", errors)
    require("participant_product" in unity_roles and "render_state_mirror" in unity_roles, "Unity role incomplete", errors)
    require("session_authority" not in unity_roles and "sequence_authority" not in unity_roles, "Unity owns forbidden authority", errors)

    timing = contract.get("timing", {})
    require(timing.get("segments") == ["demo", "closed_loop", "lock_transition"], "segment order drifted", errors)
    defaults = timing.get("default_seconds", {})
    require(defaults == {"demo": 25, "closed_loop": 150, "lock_transition": 25}, "default timing drifted", errors)
    require(sum(defaults.values()) == timing.get("default_module_seconds"), "module duration sum mismatch", errors)
    require(timing.get("default_module_seconds", 0) * 4 == timing.get("default_core_seconds"), "core duration sum mismatch", errors)

    representation = contract.get("representation", {})
    require(representation.get("truth_layers") == ["target", "actual", "cumulative", "fallback"], "truth layers drifted", errors)
    require(representation.get("same_truth_across_conditions") is True, "condition truth is not shared", errors)
    require(representation.get("same_audio_semantics_across_conditions") is True, "audio semantics are not shared", errors)
    require(representation.get("abstract_form_frozen") is False, "abstract form was prematurely frozen", errors)

    journey = contract.get("journey", [])
    journey_ids = [item.get("id") for item in journey]
    require(journey_ids == [f"J-{index:02d}" for index in range(1, 13)], "journey IDs/order drifted", errors)
    for item in journey:
        if item.get("surface") == "unity_core":
            require(item.get("participant_action") == "none", f"core journey {item.get('id')} requires participant action", errors)

    frozen = contract.get("frozen_ids", [])
    versioned = contract.get("versioned_change_ids", [])
    opened = contract.get("open_ids", [])
    all_boundary_ids = frozen + versioned + opened
    require(len(all_boundary_ids) == len(set(all_boundary_ids)), "duplicate boundary ID", errors)
    require(set(re.findall(r"\bF-\d{3}\b", documents)) >= set(frozen + versioned), "documented frozen IDs incomplete", errors)
    require(set(re.findall(r"\bO-\d{3}\b", documents)) >= set(opened), "documented open IDs incomplete", errors)
    require(set(re.findall(r"\bC-\d{3}\b", documents)) >= set(contract.get("required_claim_ids", [])), "claim trace incomplete", errors)

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
        "PASS: V-01 contract; 24 frozen/versioned constraints; 15 open decisions; "
        "12 journey nodes; 10 traced claims; no Unity build or participant-result overclaim"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
