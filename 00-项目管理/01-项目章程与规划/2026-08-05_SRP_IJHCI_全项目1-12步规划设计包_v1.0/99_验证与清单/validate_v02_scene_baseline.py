"""Validate the V-02 scene-design baseline and its authority boundaries."""

from __future__ import annotations

import csv
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
V02 = ROOT / "20_产品与场景设计" / "V-02_天气概念与呼吸提示专项原型"
CONTRACT = V02 / "v02-scene-baseline-v1.0.json"
PROTOCOL = ROOT / "00_总控" / "protocol_authority_v1.1.json"
V01_CONTRACT = (
    ROOT
    / "20_产品与场景设计"
    / "V-01_研究体验契约与完整旅程"
    / "v01-experience-contract-v1.0.json"
)
R01_SCHEMA = (
    ROOT
    / "20_产品与场景设计"
    / "R-01_四层表示方案"
    / "r01-four-layer-representation-v0.9.schema.json"
)
REGISTRY = ROOT / "24_团队任务与项目治理" / "05_可领取任务包.csv"
DOCUMENTS = (
    V02 / "README.md",
    V02 / "CONTEXT.md",
    V02 / "V-02_四场景确认与移交基线.md",
    V02 / "V-02_设计决策日志.md",
    V02 / "V-02_节点5_风雨隘口与雨幕风门规格.md",
    V02 / "V-02_节点6_热浪盐原与冷流风道规格.md",
    V02 / "V-02_节点7_雪雾松林与粉雪升沉规格.md",
    V02 / "V-02_节点8_灰霾湿地与色潮回流规格.md",
    V02 / "V-02_节点12_两条件公平矩阵.md",
    V02 / "ADR-026_V-02收口于场景确认.md",
    V02 / "V-02_技术验收记录_已签署.md",
)
MODULES = {
    "storm": ("风雨隘口", "雨幕风门", "box_3_3_3_3"),
    "heat": ("热浪盐原", "冷流风道", "long_exhale_4_6"),
    "snow": ("雪雾松林", "粉雪升沉", "equal_inhale_exhale_5_5"),
    "fade": ("灰霾湿地", "色潮回流", "double_inhale_long_exhale"),
}
RESTRICTED_TERMS = ("诊断", "治疗", "疾病", "患者", "医疗设备", "临床")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_object(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def main() -> int:
    errors: list[str] = []
    for path in (*DOCUMENTS, CONTRACT, PROTOCOL, V01_CONTRACT, R01_SCHEMA, REGISTRY):
        require(path.is_file(), f"missing file: {path}", errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    try:
        contract = load_object(CONTRACT)
        protocol = load_object(PROTOCOL)
        v01_contract = load_object(V01_CONTRACT)
        r01_schema = load_object(R01_SCHEMA)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: invalid JSON authority: {exc}")
        return 1

    require(contract.get("contract_id") == "SRP-V02-SCENE-BASELINE", "wrong contract_id", errors)
    require(contract.get("version") == "1.0.0", "wrong version", errors)
    require(contract.get("status") == "CANDIDATE_FOR_REVIEW", "wrong contract status", errors)
    require(contract.get("scope") == "scene_design_confirmation", "wrong scope", errors)

    authority = contract.get("authority", {})
    formal_runtime = protocol.get("formal_runtime", {})
    require(authority.get("sequence") == "python_manifest", "sequence authority drifted", errors)
    require(authority.get("session_clock") == "python", "clock authority drifted", errors)
    require(authority.get("target_protocol") == "python", "target authority drifted", errors)
    require(
        authority.get("touchdesigner_role") == "optional_read_only_console",
        "TouchDesigner authority drifted",
        errors,
    )
    require(authority.get("participant_input_during_core") is False, "participant input enabled", errors)
    require(authority.get("spout_used") is False and formal_runtime.get("spout_forbidden") is True, "Spout boundary drifted", errors)
    require(formal_runtime.get("python_is_authority") is True, "protocol Python authority drifted", errors)
    require(formal_runtime.get("unity_independent_of_td") is True, "Unity independence drifted", errors)
    require(formal_runtime.get("td_read_only") is True, "protocol TD read-only boundary drifted", errors)

    technical_ids = contract.get("technical_ids", [])
    require(
        isinstance(technical_ids, list)
        and len(technical_ids) == len(set(technical_ids))
        and set(technical_ids) == set(MODULES),
        "technical ID set or uniqueness drifted",
        errors,
    )
    require(contract.get("module_occurrence") == "exactly_once", "module occurrence drifted", errors)
    modules = contract.get("modules", [])
    require(isinstance(modules, list) and len(modules) == 4, "modules must contain four entries", errors)
    indexed = {item.get("technical_id"): item for item in modules if isinstance(item, dict)}
    require(set(indexed) == set(MODULES), "module ID set drifted", errors)
    for module_id, (scene, mechanism, breathing) in MODULES.items():
        item = indexed.get(module_id, {})
        require(item.get("visible_scene") == scene, f"{module_id} scene drifted", errors)
        require(item.get("core_mechanism") == mechanism, f"{module_id} mechanism drifted", errors)
        require(item.get("breathing_structure") == breathing, f"{module_id} breathing structure drifted", errors)
        for role in ("target_role", "actual_role", "recovery_role"):
            require(bool(item.get(role)), f"{module_id} missing {role}", errors)
    for module_id in ("storm", "fade"):
        require(
            indexed.get(module_id, {}).get("contract_requirement")
            == "F-01_v2.2_REQUIRED_BEFORE_IMPLEMENTATION",
            f"{module_id} v2.2 gate missing",
            errors,
        )

    research_design = v01_contract.get("research_design", {})
    require(set(research_design.get("module_ids", [])) == set(MODULES), "V-01 module IDs drifted", errors)
    require(research_design.get("module_occurrence") == "exactly_once", "V-01 module occurrence drifted", errors)
    require(
        research_design.get("stage_1_conditions") == ["scene_native", "abstract_pacer"],
        "V-01 cue conditions drifted",
        errors,
    )
    expected_layers = {"target", "actual", "cumulative", "fallback"}
    for mode in ("scene_native", "abstract_pacer"):
        package = research_design.get("condition_packages", {}).get(mode, {})
        require(set(package.get("truth_layers", [])) == expected_layers, f"V-01 {mode} truth layers drifted", errors)
        require(set(package.get("module_ids", [])) == set(MODULES), f"V-01 {mode} modules drifted", errors)

    layer_properties = (
        r01_schema.get("properties", {})
        .get("layers", {})
        .get("properties", {})
    )
    schema_sources = {
        layer: layer_properties.get(layer, {}).get("properties", {}).get("source", {}).get("const")
        for layer in expected_layers
    }
    expected_sources = {
        "target": "python.target_protocol",
        "actual": "python.interaction_state_estimate",
        "cumulative": "python.recovery_aggregate",
        "fallback": "python.signal_quality",
    }
    require(schema_sources == expected_sources, "R-01 layer source authority drifted", errors)
    require(contract.get("layer_sources") == expected_sources, "V-02 layer sources drifted", errors)

    world = contract.get("world", {})
    require(world.get("presentation") == "layered_2d_horizontal_auto_scroll", "presentation drifted", errors)
    require(world.get("order_independent_units") is True, "scene units are not order independent", errors)
    require(world.get("base_weather_driven_by_breathing") is False, "base weather leaks breathing", errors)
    require(world.get("camera_driven_by_breathing") is False, "camera leaks breathing", errors)

    cues = contract.get("cue_conditions", {})
    require(cues.get("modes") == ["scene_native", "abstract_pacer"], "cue modes drifted", errors)
    for key in ("mutually_exclusive", "same_truth", "same_timing", "same_audio"):
        require(cues.get(key) is True, f"cue condition rule {key} drifted", errors)
    require(cues.get("abstract_pacer", {}).get("form") == "centered_unfilled_double_ring", "abstract cue form drifted", errors)

    assets = contract.get("asset_baseline", {})
    require(assets.get("production_route") == "ai_led_layered_full_canvas_png", "asset production route drifted", errors)
    require(assets.get("runtime_authority") == "accepted_png_layers_and_composition_manifest", "asset runtime authority drifted", errors)
    for key in ("shared_canvas_origin", "provenance_and_license_required", "g02_release_gate_required"):
        require(assets.get(key) is True, f"asset rule {key} drifted", errors)

    deferred = set(contract.get("deferred_to_downstream", []))
    require({"runtime_prototype", "implementation_risk_ranking", "formative_review_protocol"} <= deferred, "downstream deferrals incomplete", errors)
    evidence = contract.get("evidence_state", {})
    require(evidence.get("scene_design") == "CONFIRMED_CANDIDATE", "scene evidence status drifted", errors)
    require(evidence.get("unity_runtime") == "NOT_IMPLEMENTED_BY_V02", "Unity evidence overclaimed", errors)
    require(evidence.get("participant_results") == "NOT_OBSERVED", "participant evidence overclaimed", errors)

    document_text = "\n".join(path.read_text(encoding="utf-8-sig") for path in DOCUMENTS)
    for term in RESTRICTED_TERMS:
        require(term not in document_text, f"restricted wording present: {term}", errors)
    require("SCENE_DESIGN_CONFIRMED" in document_text, "scene confirmation marker missing", errors)
    require("REMOVED_FROM_V-02" in document_text, "node 15 removal marker missing", errors)
    require("SUPERSEDED" in document_text, "superseded review decision not recorded", errors)
    transfer_text = (V02 / "V-02_四场景确认与移交基线.md").read_text(encoding="utf-8-sig")
    transfer_lines = transfer_text.splitlines()
    for module_id, (scene, mechanism, _) in MODULES.items():
        require(
            any(
                line.startswith(f"| `{module_id}` |")
                and scene in line
                and mechanism in line
                for line in transfer_lines
            ),
            f"Markdown transfer baseline drifted for {module_id}",
            errors,
        )

    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["task_id"]: row for row in csv.DictReader(handle)}
    row = rows.get("V-02", {})
    require(row.get("title") == "【Unity前期设计】四天气场景与呼吸提示设计确认", "registry title drifted", errors)
    require("动态原型" not in row.get("deliverables", ""), "V-02 still requires a runtime prototype", errors)
    require("形成性评审" not in row.get("evidence_required", ""), "V-02 still requires formative review evidence", errors)
    require("场景设计确认" in row.get("completion_condition", ""), "registry completion boundary drifted", errors)
    f05 = rows.get("F-05", {})
    require(
        f05.get("status") in {"WAIT_DEP", "READY", "IN_PROGRESS", "IN_REVIEW", "DONE"},
        "F-05 versioned contract task missing or invalid",
        errors,
    )
    require("v2.2" in f05.get("title", ""), "F-05 v2.2 ownership missing", errors)
    require(
        set(f05.get("depends_on", "").split("|")) == {"F-01", "P-01", "P-02"},
        "F-05 dependency boundary drifted",
        errors,
    )
    for task_id in ("U-01", "U-02", "T-01", "U-07"):
        require("F-05" in rows.get(task_id, {}).get("depends_on", "").split("|"), f"{task_id} does not depend on F-05", errors)
    require("G-02" in rows.get("U-08", {}).get("depends_on", "").split("|"), "U-08 does not depend on G-02", errors)
    require("工程风险排序" in rows.get("V-03", {}).get("deliverables", ""), "V-03 risk-ranking ownership missing", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V-02 scene baseline; modules=4; cue_modes=2; runtime_claim=NOT_IMPLEMENTED_BY_V02")
    return 0


if __name__ == "__main__":
    sys.exit(main())
