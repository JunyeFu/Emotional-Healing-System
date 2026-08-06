"""Validate the executable SRP protocol authority and stale-design firewall."""

from __future__ import annotations

import json
import pathlib
import sys


PACKAGE = pathlib.Path(__file__).resolve().parents[1]
AUTHORITY = PACKAGE / "00_总控" / "protocol_authority_v1.1.json"

ACTIVE_FILES = [
    PACKAGE / "README.md",
    PACKAGE / "00_总控" / "01_十二步路线图与状态.md",
    PACKAGE / "00_总控" / "02_当前状态与不可跨越门禁.md",
    PACKAGE / "00_总控" / "03_项目研究论文成果一体化.md",
    PACKAGE / "00_总控" / "04_2026_2027建议主计划.md",
    PACKAGE / "00_总控" / "05_风险登记册.csv",
    PACKAGE / "00_总控" / "06_成果登记册.csv",
    PACKAGE / "00_总控" / "13_IJHCI独立审稿攻击与升级裁定_v1.1.md",
    PACKAGE / "02_步骤01_课题主张与顶层设计" / "00_第1步计划.md",
    PACKAGE / "03_步骤02_构念比较条件与测量" / "00_第2步计划.md",
    PACKAGE / "04_步骤03_伦理预试样本量" / "00_第3步计划.md",
    PACKAGE / "10_步骤09_LevelC技术预试与预注册" / "00_第9步计划.md",
    PACKAGE / "10_步骤09_LevelC技术预试与预注册" / "01_详细执行方案.md",
    PACKAGE / "11_步骤10_正式研究执行" / "00_第10步计划.md",
    PACKAGE / "11_步骤10_正式研究执行" / "01_详细执行方案.md",
    PACKAGE / "12_步骤11_离线处理分析与论文写作" / "00_第11步计划.md",
    PACKAGE / "12_步骤11_离线处理分析与论文写作" / "01_详细执行方案.md",
    PACKAGE / "20_产品与场景设计" / "00_参与者产品总规格.md",
    PACKAGE / "21_真实设备与在线运行系统" / "06_目标运行接口_v2.md",
    PACKAGE / "22_离线处理与科研分析" / "01_核心数据字典.csv",
    PACKAGE / "22_离线处理与科研分析" / "02_QC与分析集规则.md",
    PACKAGE / "22_离线处理与科研分析" / "03_呼吸事件与Protocol_Fidelity.md",
    PACKAGE / "22_离线处理与科研分析" / "05_问卷与访谈处理.md",
    PACKAGE / "22_离线处理与科研分析" / "06_统计模型与图表计划.md",
    PACKAGE / "23_后续可解释序列编排研究" / "00_后续研究总设计.md",
    PACKAGE / "23_后续可解释序列编排研究" / "01_数据与方法储备.md",
    PACKAGE / "24_团队任务与项目治理" / "00_四人团队职责与任务树.md",
    PACKAGE / "24_团队任务与项目治理" / "04_可领取树型任务包_v2.0.md",
    PACKAGE / "24_团队任务与项目治理" / "05_可领取任务包.csv",
    PACKAGE / "25_论文投稿与成果交付" / "00_IJHCI论文结构.md",
    PACKAGE / "25_论文投稿与成果交付" / "01_主张证据矩阵.csv",
    PACKAGE / "25_论文投稿与成果交付" / "01_核心贡献_IJHCI立足性论证_v1.0.md",
    PACKAGE / "25_论文投稿与成果交付" / "02_投稿返修检查表.md",
]

FORBIDDEN_STALE_MARKERS = (
    "统一120秒",
    "参与者8分钟",
    "104人",
    "208次访视",
    "24人双访视",
    "每人完成两次",
    "两实验日SOP",
    "FAS/PPS",
    "第一篇提示论文",
)

REQUIRED_MARKERS = {
    PACKAGE / "00_总控" / "13_IJHCI独立审稿攻击与升级裁定_v1.1.md": (
        "REJECT_AND_RESUBMIT_DESIGN",
        "PLANNED_NOT_OBSERVED",
        "三个互不共享结论的只读审稿角色",
    ),
    PACKAGE / "20_产品与场景设计" / "00_参与者产品总规格.md": (
        "完整表示方案",
        "正式构建不依赖Spout、TD或Mock",
    ),
    PACKAGE / "21_真实设备与在线运行系统" / "06_目标运行接口_v2.md": (
        "四时间戳",
        "等效外部方法验证",
        "PolicyDecision",
        "LIVE_E2E",
    ),
    PACKAGE / "22_离线处理与科研分析" / "03_呼吸事件与Protocol_Fidelity.md": (
        "expected_cycle_opportunity",
        "TECH_UNOBSERVABLE",
    ),
    PACKAGE / "22_离线处理与科研分析" / "06_统计模型与图表计划.md": (
        "四层理解",
        "randomization_strata",
        "FDR",
    ),
    PACKAGE / "22_离线处理与科研分析" / "05_问卷与访谈处理.md": (
        "先完成PANAS后测",
        "研究目的和条件猜测",
    ),
    PACKAGE / "23_后续可解释序列编排研究" / "00_后续研究总设计.md": (
        "参与者分组交叉拟合",
        "有效样本量",
        "行为概率",
        "离线策略价值",
    ),
    PACKAGE / "25_论文投稿与成果交付" / "00_IJHCI论文结构.md": (
        "部署扩展",
        "完整提示表示方案",
        "相同的`scene_native` Unity构建",
    ),
}

HISTORICAL_FILES = [
    PACKAGE / "00_总控" / "09_Codex重梳理工作稿.md",
    PACKAGE / "00_总控" / "10_重新梳理结论与下一确认门.md",
    PACKAGE / "00_总控" / "11_实现冻结基线_v1.0.md",
    PACKAGE / "00_总控" / "12_IJHCI课题升级决策_v1.0.md",
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    data = json.loads(AUTHORITY.read_text(encoding="utf-8"))

    checks = {
        "schema_version": data.get("schema_version") == "1.1",
        "status": data.get("status") == "REJECT_AND_RESUBMIT_DESIGN",
        "single_participation": data["participant_rule"]["one_core_experience"] is True,
        "core_seconds": data["core_experience"]["recommended_total_seconds"] == 800,
        "level_c": data["stages"]["level_c"]["target_total"] == 48,
        "stage_1": data["stages"]["stage_1"]["complete_target_total"] == 192,
        "stage_3": data["stages"]["stage_3"]["complete_target_total"] == 192,
        "gate_1_margin": data["gates"]["gate_1"]["noninferiority_margin"] == 0.075,
        "scci_role": data["gates"]["gate_2"]["scci_role"] == "manipulation_check",
        "joint_gate_2": data["gates"]["gate_2"]["ordered_components"] == [
            "scci_superiority",
            "four_layer_comprehension_noninferiority",
            "mental_effort_noninferiority",
        ],
        "policy_unit": data["analysis"]["primary_unit"] == "participant",
        "no_sequence_fixed_effect": data["analysis"]["sequence_24_in_primary_model"] is False,
        "participant_grouped_policy": data["stages"]["stage_2"]["method"]
        == "participant_grouped_cross_fitted_finite_horizon_ridge_q",
        "policy_exploration_floor": data["stages"]["stage_2"]["minimum_uniform_mixture"]
        == 0.20,
        "stage_3_same_build": data["stages"]["stage_3"]["same_scene_native_build"] is True,
        "questionnaire_order": data["questionnaire_order"] == [
            "device_setup_and_standardized_training",
            "panas_pre",
            "four_module_core_experience",
            "panas_post",
            "scci_and_secondary_measures",
            "purpose_and_condition_guess",
            "qualitative_subsample",
        ],
        "unity_no_td": data["formal_runtime"]["unity_independent_of_td"] is True,
        "no_spout": data["formal_runtime"]["spout_forbidden"] is True,
        "no_mock": data["formal_runtime"]["mock_forbidden"] is True,
        "live_e2e": data["formal_runtime"]["live_e2e_required"] is True,
        "capacity": data["capacity"]["station_hours_range"] == [484, 616],
    }
    for name, passed in checks.items():
        if not passed:
            fail(errors, f"authority check failed: {name}")

    for path in ACTIVE_FILES:
        text = path.read_text(encoding="utf-8-sig")
        for marker in FORBIDDEN_STALE_MARKERS:
            if marker in text:
                fail(errors, f"{path.relative_to(PACKAGE)} contains stale marker {marker!r}")

    for path, markers in REQUIRED_MARKERS.items():
        text = path.read_text(encoding="utf-8-sig")
        for marker in markers:
            if marker not in text:
                fail(errors, f"{path.relative_to(PACKAGE)} missing v1.1 marker {marker!r}")

    for path in HISTORICAL_FILES:
        if "SUPERSEDED_FOR_EXECUTION" not in path.read_text(encoding="utf-8-sig"):
            fail(errors, f"{path.relative_to(PACKAGE)} is not marked historical")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("PASS: protocol authority v1.1 and active execution files are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
