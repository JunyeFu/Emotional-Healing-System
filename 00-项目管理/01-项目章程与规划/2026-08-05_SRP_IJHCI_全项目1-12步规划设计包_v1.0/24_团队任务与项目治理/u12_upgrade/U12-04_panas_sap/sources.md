# U12-04 PANAS 主结果 SAP 与新功效规格 — 参数来源

任务：【统计规格】PANAS 主结果 SAP 与新功效规格（W1 波次；4 人日；FIXED；process_profile=P-ANALYSIS；前置 U12-01、F-02 均 DONE）
交付目录：`24_团队任务与项目治理/u12_upgrade/U12-04_panas_sap/`
本文件：每个 SAP/功效规格参数指向权威来源，禁止无来源参数。

## 权威输入快照

- 输入快照 ID：`236F924514D791AE5506457027E2598CE5C27B29F6A0CE39101F3262142843C3`
- 来源：`当前解锁独立任务包/U12-04/package_manifest.json`
- 哈希策略：`sha256_lf_no_trailing_ws_text_v1`（UTF8→LF→逐行去尾空白→UTF8 无 BOM→SHA256 大写）
- 输入文件清单（7 项，SHA-256 见 package_manifest.json）：
  1. `00_总控/protocol_authority_v1.2.json`（唯一权威契约）
  2. `u12_upgrade/consumers.json`
  3. `u12_upgrade/study_manifest_v1.2.template.json`
  4. `audit_upgrade/release_routes_v1.2.json`
  5. `audit_upgrade/task_milestones_v1.2.json`
  6. `2026-09-08_SRP_v1.2_当前解锁独立任务包/tasks/U12-04/inputs/task_input.json`
  7. `a03_gate2_spec/scoring.py`

## 主结果参数来源

| 参数 | 值 | 来源 |
| --- | --- | --- |
| stage | stage_1 | protocol_authority_v1.2.json `primary.stage` |
| outcome | panas_negative_affect_post_adjusted_for_pre | protocol_authority_v1.2.json `primary.outcome` |
| contrast | native_minus_abstract（native=1, abstract=0） | protocol_authority_v1.2.json `primary.contrast` |
| 方向 | lower_is_better=true | protocol_authority_v1.2.json `primary.lower_is_better` |
| 模型 | `NA_post ~ cue_mode + centered_NA_pre + randomization_strata` | protocol_authority_v1.2.json `primary.candidate_model` |
| 方差 | HC3 | protocol_authority_v1.2.json `primary.candidate_variance` |
| 检验 | two_sided | protocol_authority_v1.2.json `primary.test` |
| α | 0.05 | protocol_authority_v1.2.json `primary.alpha` |
| CI | 0.95 | protocol_authority_v1.2.json `primary.ci_level` |
| 单位 | participant | protocol_authority_v1.2.json `primary.unit` |
| 基线协变量 | pretreatment_baseline_required=true | protocol_authority_v1.2.json `primary.pretreatment_baseline_required` |
| 后处理协变量 | post_treatment_covariates_in_primary_model=false | protocol_authority_v1.2.json `primary.post_treatment_covariates_in_primary_model` |
| 功能护栏失败仍报告主结果 | report_even_if_functional_guard_fails=true | protocol_authority_v1.2.json `primary.report_even_if_functional_guard_fails` |
| 最小重要差值 | null（UNFROZEN） | protocol_authority_v1.2.json `primary.minimum_important_affect_difference` |

## 功能护栏参数来源

| 参数 | 值 | 来源 |
| --- | --- | --- |
| outcome | opportunity_based_participant_protocol_fidelity | protocol_authority_v1.2.json `functional_guard.outcome` |
| 差值 | native_minus_abstract | protocol_authority_v1.2.json `functional_guard.difference` |
| 非劣效界值 | 0.075（INHERITED_REQUIRES_JUSTIFICATION） | protocol_authority_v1.2.json `functional_guard.noninferiority_margin_candidate` |
| 分析集 | [all_randomized, complete_four_module] | protocol_authority_v1.2.json `functional_guard.analysis_sets` |
| 双集同过才可主张 | both_must_pass_for_native_substitution_claim=true | protocol_authority_v1.2.json `functional_guard.both_must_pass_for_native_substitution_claim` |

## 操纵检查 / 等效性 / 缺失处理

| 参数 | 值 | 来源 |
| --- | --- | --- |
| 操纵检查工具 | SCCI | protocol_authority_v1.2.json `manipulation_check.instrument` |
| 角色 | manipulation_only | protocol_authority_v1.2.json `manipulation_check.role` |
| 不阻断主结果报告 | blocks_prespecified_outcome_reporting=false | protocol_authority_v1.2.json `manipulation_check.blocks_prespecified_outcome_reporting` |
| 操纵失败不单独作废随机比较 | failure_alone_invalidates_randomized_comparison=false | protocol_authority_v1.2.json `manipulation_check.failure_alone_invalidates_randomized_comparison` |
| 等效性 | confirmatory_enabled=false | protocol_authority_v1.2.json `equivalence.confirmatory_enabled` |
| 不显著≠等效 | not_significant_is_not_equivalent=true | protocol_authority_v1.2.json `equivalence.not_significant_is_not_equivalent` |
| affect/sensor 分离 | affect_and_sensor_separated=true | protocol_authority_v1.2.json `missingness.affect_and_sensor_separated` |
| 传感器失败不丢有效 PANAS | sensor_failure_does_not_drop_valid_panas=true | protocol_authority_v1.2.json `missingness.sensor_failure_does_not_drop_valid_panas` |
| 插补候选 | 100 | protocol_authority_v1.2.json `missingness.candidate_imputations` |
| 缺失机制 | SAP_FREEZE_REQUIRED | protocol_authority_v1.2.json `missingness.status` |

## 样本规划 / 序列随机化

| 参数 | 值 | 来源 |
| --- | --- | --- |
| level_c 锚点 | 48 | protocol_authority_v1.2.json `sample_planning.level_c_anchor` |
| 旧完成目标 | 192 | protocol_authority_v1.2.json `sample_planning.stage_1_old_complete_target` |
| 旧招募上限 | 240 | protocol_authority_v1.2.json `sample_planning.stage_1_old_recruitment_cap` |
| 正式随机化 N | null（UNFROZEN） | protocol_authority_v1.2.json `sample_planning.formal_randomized_n` |
| 功效目标 | 0.9（candidate） | protocol_authority_v1.2.json `sample_planning.main_power_target_candidate` |
| 旧锚点非最终功效 | old_anchors_are_not_final_power=true | protocol_authority_v1.2.json `sample_planning.old_anchors_are_not_final_power` |
| 每臂平衡序列 | 24 | protocol_authority_v1.2.json `sequence.stage_1_balanced_sequences_per_arm` |
| 分配块 | 48（candidate） | protocol_authority_v1.2.json `sequence.allocation_block_size_candidate` |
| 平衡单位 | assigned_not_complete | protocol_authority_v1.2.json `sequence.balance_unit` |
| 禁完成补位 | completion_based_refilling_forbidden=true | protocol_authority_v1.2.json `sequence.completion_based_refilling_forbidden` |
| 禁结果依赖提前停止 | outcome_based_optional_stopping_forbidden=true | protocol_authority_v1.2.json `sequence.outcome_based_optional_stopping_forbidden` |

## 功效模拟规格参数来源

| 参数 | 值 | 来源 |
| --- | --- | --- |
| 确定性种子 | 20260906 | 沿用 a03_gate2_spec/simulation.py（seed=20260906 惯例） |
| 分析集 | PRIMARY_CONSERVATIVE / OBSERVED_CASE | 沿用 a03_gate2_spec/simulation.py `ANALYSIS_SETS` 双集惯例，语义映射本 SAP 分析集 |
| Monte Carlo 次数 | 1000 | 沿用 a03_gate2_spec/simulation.py（replications=1000） |
| 主模型/方差/检验/α | 同主结果参数（HC3、two_sided、0.05） | protocol_authority_v1.2.json `primary.*` |
| N 网格 | [48, 96, 144, 192, 240] | 覆盖旧锚点：48（level_c）、192（完成目标）、240（招募上限） |
| 效应网格（Cohen's d） | [0.2, 0.3, 0.4, 0.5] | 本规格合成参考（UNFROZEN），真实效应未冻结 |
| 目标功效 | 0.9 | protocol_authority_v1.2.json `sample_planning.main_power_target_candidate` |
| N/效应冻结 | 否（n_frozen=false, effect_frozen=false） | protocol_authority_v1.2.json `sample_planning.old_anchors_are_not_final_power` + task_input（formal N 待真实冻结） |
| 数据生成 | rho_pre_post=0.5、strata 效应 0.1、缺失 native 0.02 / abstract 0.01 | 合成假设（SYNTHETIC_ONLY，非真实校准） |

## 运行时契约参数来源

| 参数 | 值 | 来源 |
| --- | --- | --- |
| python_is_authority | true | protocol_authority_v1.2.json `formal_runtime.python_is_authority` |
| 遥测频率 | 20 Hz | protocol_authority_v1.2.json `formal_runtime.telemetry_hz` |
| 运行时契约版本 | 2.2 | protocol_authority_v1.2.json `formal_runtime.runtime_contract_version` |
| live_e2e | 必需 | protocol_authority_v1.2.json `formal_runtime.live_e2e_required` |
| spout/mock | 禁用 | protocol_authority_v1.2.json `formal_runtime.spout_forbidden` / `mock_forbidden` |

## 交付物清单与验收对应

| 交付物 | 文件 | 验收对应 |
| --- | --- | --- |
| SAP 文档 | sap.md | AC1 可追溯；主结果/差值方向/参数来源/功效规格 |
| 机器合同 | contract.json | AC1/AC2 字段级可验证 |
| 功效模拟规格 | power_spec.json | AC2 N/界值不冻结、双分析集 |
| 功效模拟代码 | power_simulation.py | AC2 确定性 Monte Carlo、双侧 HC3 |
| 功效网格/报告 | power_grid.json、power_report.md | AC2 覆盖 N×效应 |
| 参数来源 | sources.md（本文件） | AC1 每个参数可回溯 |
| 校验/测试/证据 | validate.py、test_contract.py、build_evidence.py、evidence.json | AC3 证据与提交绑定 |

## 声明边界（全部不主张）

- 全项目因果效应：false
- 独立天气效应：false
- 独立呼吸结构效应：false
- 单一视觉机制效应：false
- 长期效应：false
- 短长交互：false
- 诊断/治疗有效性：false

来源字段：protocol_authority_v1.2.json `claim_boundaries.*`（全部 false）。

## 复核与签收

- 本包为 DESIGN_AND_SYNTHETIC_ONLY：合成功效参数不构成正式样本量声明。
- 正式冻结（minimum_important_affect_difference / missingness_and_mnar / functional_margin_justification / final_power_and_n 等 15 项）须在真实数据可用前完成。
- 真实第二人签收由任务治理流程执行；本包不代签外部条件。
