from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASE = (
    ROOT
    / "00-项目管理"
    / "01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
    / "20_产品与场景设计"
    / "V-03_四层视听映射与资产来源基线"
)


def main() -> None:
    plan_path = BASE / "V-03_前期规划与上下游对齐_v1.0.md"
    baseline_path = BASE / "v03-planning-baseline-v1.0.json"
    readme_path = BASE / "README.md"

    for path in (plan_path, baseline_path, readme_path):
        assert path.is_file(), f"missing V-03 preparation artifact: {path}"

    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert data["status"] == "READY_FOR_DETAILED_FILL_WITH_F05_PARTIAL_BLOCK"
    assert data["task_status_authority"] == "IN_PROGRESS"
    assert set(data["technical_ids"]) == {"storm", "heat", "snow", "fade"}
    assert set(data["cue_modes"]) == {"scene_native", "abstract_pacer"}
    assert len(data["deliverable_templates"]) == 6
    assert len(data["risk_dimensions"]) == 7

    required_consumers = {
        "U-02",
        "V-04",
        "V-05",
        "U-03",
        "U-04",
        "U-05",
        "U-06",
        "U-07",
        "G-02",
        "U-08",
    }
    assert set(data["downstream_consumers"]) == required_consumers

    fill = data["detailed_fill_state"]
    assert fill["mapping_rows"] == "TBD_EXECUTION"
    assert fill["parameter_values"] == "TBD_EXECUTION"
    assert fill["weather_risk_scores"] == "TBD_EXECUTION"
    assert fill["u03_selected_weather"] is None
    assert fill["storm_phase_instances"] == "BLOCKED_F05"
    assert fill["fade_phase_instances"] == "BLOCKED_F05"

    plan = plan_path.read_text(encoding="utf-8")
    for required_text in (
        "Python",
        "Unity",
        "TouchDesigner",
        "TargetCue",
        "ActualFeedback",
        "RecoveryState",
        "FallbackState",
        "READY_FOR_DETAILED_FILL_WITH_F05_PARTIAL_BLOCK",
    ):
        assert required_text in plan, f"missing planning boundary: {required_text}"

    print(
        "PASS: V-03 preparation baseline; "
        "deliverable_templates=6; risk_dimensions=7; "
        "detailed_fill=TBD; F05_partial_block=active"
    )


if __name__ == "__main__":
    main()
