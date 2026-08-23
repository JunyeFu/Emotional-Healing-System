from __future__ import annotations

import itertools
import json
import runpy
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # The repository's frozen runner is `py -3.14`.
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parents[4]
BASE = (
    ROOT
    / "00-项目管理"
    / "01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
    / "20_产品与场景设计"
    / "V-03_四层视听映射与资产来源基线"
)
GENERATOR = Path(__file__).with_name("generate_v03_contracts.py")


DOCS = (
    "V-03_四层视听映射合同_v1.0.md",
    "V-03_参数边界与锁定规则_v1.0.md",
    "V-03_两条件信息匹配审查_v1.0.md",
    "V-03_声音角色表_v1.0.md",
    "V-03_资产来源与替换计划_v1.0.md",
    "V-03_工程风险矩阵与U-03选择_v1.0.md",
)
MACHINE_FILES = (
    "V-03_四层视听映射合同_v1.0.json",
    "V-03_四层视听映射合同_v1.0.schema.json",
    "V-03_参数边界与锁定规则_v1.0.json",
    "V-03_工程风险评分_v1.0.json",
)
FORBIDDEN_WORDS = (
    "\u8bca\u65ad",
    "\u6cbb\u7597",
    "\u75be\u75c5",
    "\u60a3\u8005",
    "\u533b\u7597\u8bbe\u5907",
    "\u4e34\u5e8a",
)


def load_json(name: str) -> dict[str, object]:
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def main() -> None:
    for name in (*DOCS, *MACHINE_FILES):
        assert (BASE / name).is_file(), f"missing V-03 deliverable: {name}"
    assert GENERATOR.is_file(), "missing V-03 contract generator"

    generated = runpy.run_path(str(GENERATOR))
    mapping = load_json(MACHINE_FILES[0])
    schema = load_json(MACHINE_FILES[1])
    parameters = load_json(MACHINE_FILES[2])
    risk_data = load_json(MACHINE_FILES[3])
    assert mapping == generated["mapping_contract"](), "mapping JSON drifted from generator"
    assert schema == generated["mapping_schema"](), "mapping Schema drifted from generator"
    assert parameters == generated["parameter_contract"](), "parameter JSON drifted from generator"
    assert risk_data == generated["risk_contract"](), "risk JSON drifted from generator"
    assert mapping["schema_id"] == "V03_DESIGN_SEMANTICS_1_0"
    assert schema["$id"] == "urn:srp:v03:design-semantics:1.0"
    draft_validation_active = Draft202012Validator is not None
    if draft_validation_active:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(mapping)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["rows"]["items"]["additionalProperties"] is False

    technical_ids = ("storm", "heat", "snow", "fade")
    cue_modes = ("scene_native", "abstract_pacer")
    layers = ("target", "actual", "recovery", "fallback", "background")
    expected_keys = set(itertools.product(technical_ids, cue_modes, layers))
    rows = mapping["rows"]
    assert mapping["row_count"] == 40 == len(rows)
    actual_keys = {
        (row["technical_id"], row["cue_mode"], row["layer"]) for row in rows
    }
    assert actual_keys == expected_keys, "mapping cross product is incomplete or duplicated"

    for row in rows:
        layer = row["layer"]
        if layer == "background":
            assert row["source_fields"] == []
            assert row["audio_role"].startswith("AUD_")
        else:
            assert row["source_fields"], f"missing source fields: {row}"
            assert row["audio_role"] == "NONE"
        if layer in {"target", "actual"}:
            assert row["design_phase_slots"]
            assert row["runtime_slot_binding"] != "NOT_APPLICABLE"
        else:
            assert row["design_phase_slots"] == []
            assert row["runtime_slot_binding"] == "NOT_APPLICABLE"
        assert all("logical_" not in field for field in row["source_fields"])

    assert mapping["r01_module_id_map"] == {
        "storm": "storm",
        "heat": "scorching",
        "snow": "blizzard",
        "fade": "fading",
    }
    composition = mapping["confidence_fallback_composition"]
    assert composition["fallback_layer_reads_actual_confidence"] is False
    assert composition["good_cap"] == 1.0
    assert composition["degraded_cap_candidate"] == 0.70
    fallback_rows = [row for row in rows if row["layer"] == "fallback"]
    assert all("actual_confidence" not in row["source_fields"] for row in fallback_rows)
    target_quality = next(row for row in rows if row["layer"] == "target")[
        "quality_behavior"
    ]
    recovery_quality = next(row for row in rows if row["layer"] == "recovery")[
        "quality_behavior"
    ]
    assert target_quality["UNUSABLE"] == "OPEN_LOOP_TARGET"
    assert target_quality["DISCONNECTED"] == "FOLLOW_PYTHON_SAFE_OPEN_LOOP_OR_ABORT"
    assert recovery_quality["UNUSABLE"] == "PAUSE_AND_LOCK_LAST_VALUE"
    assert recovery_quality["DISCONNECTED"] == "PAUSE_AND_LOCK_LAST_VALUE"
    expected_source_fields = {
        "target": ["target_phase", "target_progress"],
        "actual": ["actual_phase", "actual_progress", "actual_confidence"],
        "recovery": ["recovery_value"],
        "fallback": ["signal_quality", "fallback_state", "fallback_reason"],
        "background": [],
    }
    expected_quality = {
        layer: next(row for row in rows if row["layer"] == layer)["quality_behavior"]
        for layer in layers
    }
    for row in rows:
        assert row["source_fields"] == expected_source_fields[row["layer"]]
        assert row["quality_behavior"] == expected_quality[row["layer"]]
    layer_constraints = schema["properties"]["rows"]["items"]["allOf"][-5:]
    assert [item["if"]["properties"]["layer"]["const"] for item in layer_constraints] == list(
        layers
    )
    for item in layer_constraints:
        layer = item["if"]["properties"]["layer"]["const"]
        properties = item["then"]["properties"]
        assert properties["source_fields"]["const"] == expected_source_fields[layer]
        assert properties["quality_behavior"]["const"] == expected_quality[layer]

    profiles = mapping["weather_profiles"]
    assert profiles["storm"]["runtime_binding"] == "F-05_V2_2_REQUIRED"
    assert profiles["fade"]["runtime_binding"] == "F-05_V2_2_REQUIRED"
    assert profiles["heat"]["runtime_binding"] == "V2_1_COARSE_PHASE_DIRECT"
    assert profiles["snow"]["runtime_binding"] == "V2_1_COARSE_PHASE_DIRECT"
    assert profiles["storm"]["phase_slots"] == [
        "INHALE",
        "HOLD_1",
        "EXHALE",
        "HOLD_2",
    ]
    assert profiles["fade"]["phase_slots"] == [
        "INHALE_1",
        "INHALE_2",
        "EXHALE_1",
    ]

    common = parameters["common"]
    assert common["phase_interpolation_ms"] == [100, 250]
    assert common["recovery_low_pass_s"] == [2, 5]
    assert common["scroll_speed_viewport_per_s"] == [0.015, 0.025]
    assert common["scroll_effective_coverage_min"] == 6.75
    assert common["ambient_integrated_loudness_lufs_i"] == [-24, -20]
    assert common["ambient_true_peak_max_dbtp"] == -3
    assert parameters["shared_rules"]["same_between_cue_modes"] is True
    assert parameters["shared_rules"]["no_forced_full_endpoint"] is True

    dimensions = risk_data["dimensions"]
    assert len(dimensions) == 7
    assert set(risk_data["scorers"]) == {"A", "B"}
    for scorer in risk_data["scorers"].values():
        assert set(scorer) == set(technical_ids)
        for weather in scorer.values():
            assert set(weather["scores"]) == set(dimensions)
            assert set(weather["reasons"]) == set(dimensions)
            assert all(0 <= score <= 4 for score in weather["scores"].values())
            assert all(reason.strip() for reason in weather["reasons"].values())
            assert weather["total"] == sum(weather["scores"].values())
    assert risk_data["difference_audit"] == {
        "any_dimension_gap_gte_2": False,
        "scorer_a_top_set": ["fade"],
        "scorer_b_top_set": ["storm", "fade"],
        "top_set_difference_resolved": True,
    }
    assert risk_data["selected_u03_weather"] == "fade"
    assert risk_data["selection_status"] == "FROZEN_FOR_V03_DESIGN_HANDOFF"

    risk = (BASE / DOCS[-1]).read_text(encoding="utf-8")
    fairness = (BASE / "V-03_两条件信息匹配审查_v1.0.md").read_text(encoding="utf-8")
    assert "DUAL_SCORING_COMPLETE_DIFFERENCES_RESOLVED" in risk
    assert "评分者A逐维依据" in risk and "评分者B逐维依据" in risk
    assert "V-03冻结`fade`" in risk
    assert "平均亮度" in fairness and "≤0.05" in fairness
    assert (BASE / "V-03_独立Agent复核记录.md").is_file()

    for path in BASE.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".py"}:
            text = path.read_text(encoding="utf-8")
            for word in FORBIDDEN_WORDS:
                assert word not in text, f"forbidden wording in {path}: {word}"

    print(
        "PASS: V-03 deliverables; docs=6; mapping_rows=40; "
        "parameters=machine-checked; dual_risk_scoring=resolved; u03=fade; "
        f"draft202012_validation={'active' if draft_validation_active else 'not_available'}"
    )


if __name__ == "__main__":
    main()
