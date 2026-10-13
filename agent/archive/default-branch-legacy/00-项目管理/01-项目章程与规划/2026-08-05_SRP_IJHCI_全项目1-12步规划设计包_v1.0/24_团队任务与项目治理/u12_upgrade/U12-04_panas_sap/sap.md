# U12-04 PANAS 主结果统计分析计划（SAP）候选

> 状态：CANDIDATE_NOT_RESEARCH_FROZEN —— 这是可审查的统计规格候选，不是已完成的正式研究冻结。
> 唯一权威契约：`00_总控/protocol_authority_v1.2.json`（adoption_status=GOVERNANCE_ACCEPTED）。
> 所有正式冻结字段（N、界值、效应量、缺失机制等）保持 UNFROZEN 并给出理由，交由真实冻结流程。

## 1. 目的与范围

本 SAP 规定 SRP 阶段一（stage_1）主结果的分析规格：PANAS 负性情绪后测（以基线调整）在 native 条件与 abstract 条件之间的比较。

- **任务**：U12-04【统计规格】PANAS 主结果 SAP 与新功效规格（W1，4 人日，FIXED，P-ANALYSIS）
- **前置**：U12-01（DONE）、F-02（DONE）
- **交付物**：SAP、差值方向、参数来源、功效模拟规格
- **证据类别**：DESIGN_AND_SYNTHETIC_ONLY（合成数据功效推演；真实数据与研究冻结另由对应任务交付）

## 2. 主结果（Primary）

| 属性 | 规格 | 来源 |
|---|---|---|
| 阶段 | stage_1 | `primary.stage` |
| 结局 | panas_negative_affect_post_adjusted_for_pre | `primary.outcome` |
| 单元 | participant | `primary.unit` |
| 对比 | native_minus_abstract（native_code=1, abstract_code=0） | `primary.contrast` |
| 方向 | **lower_is_better=true**（NA_post 越低越好） | `primary.lower_is_better` |
| 模型 | `NA_post ~ cue_mode + centered_NA_pre + randomization_strata` | `primary.candidate_model` |
| 方差 | HC3（异方差稳健） | `primary.candidate_variance` |
| 检验 | two_sided 双侧 | `primary.test` |
| α | 0.05 | `primary.alpha` |
| 置信区间 | 0.95（双侧） | `primary.ci_level` |
| 结果前协变量 | 仅基线（centered_NA_pre），post_treatment_covariates=false | `primary.post_treatment_covariates_in_primary_model` |
| 基线 | 必须采集并纳入（pretreatment_baseline_required=true） | `primary.pretreatment_baseline_required` |
| 最小重要差值 | null（UNFROZEN，待真实冻结） | `primary.minimum_important_affect_difference` |

### 2.1 差值方向

- 对比方向固定为 **native − abstract**。
- 负性情绪结局 `lower_is_better=true`，因此 **若 native 组 NA_post 显著低于 abstract 组（差值 < 0），视为 native 条件更优**。
- 报告时给出点估计（差值及其 95% CI），双侧 p 值；不因 functional guard 失败而隐藏主结果报告（`report_even_if_functional_guard_fails=true`）。

### 2.2 主结果分析集

- 主结果以全随机化（all_randomized）为主要分析集；完整完成四模块者（complete_four_module）作为观测分析集。
- 功效推演按 PRIMARY_CONSERVATIVE（保守）与 OBSERVED_CASE（观测）双分析集分别计算（与 A-03-SPEC Gate2 可行性模拟的分析集约定一致）。

## 3. 功能护栏（Functional Guard）

| 属性 | 规格 | 来源 |
|---|---|---|
| 结局 | opportunity_based_participant_protocol_fidelity | `functional_guard.outcome` |
| 对比 | native_minus_abstract | `functional_guard.difference` |
| 非劣界值 | 0.075（candidate，margin_status=INHERITED_REQUIRES_JUSTIFICATION） | `functional_guard.noninferiority_margin_candidate` |
| 分析集 | [all_randomized, complete_four_module]，两者均须通过 | `functional_guard.analysis_sets` / `both_must_pass_for_native_substitution_claim` |
| 作用 | 仅用于支持 native 替代 claim；不阻断主结果报告 | `primary.report_even_if_functional_guard_fails` |

- **界值 0.075 为继承候选值，不是正式冻结界值**。正式冻结需在真实数据与机构材料可用后进行 `functional_margin_justification` 冻结。

## 4. 操纵检查（Manipulation Check）

- 工具：SCCI；角色：仅操纵（manipulation_only）。
- 不阻断预设结局报告（`blocks_prespecified_outcome_reporting=false`）。
- 操纵检查失败本身不使随机化比较失效（`failure_alone_invalidates_randomized_comparison=false`）。

## 5. 等效性（Equivalence）

- **确认性等效默认不启用**：`confirmatory_enabled=false`，margin=null。
- `not_significant_is_not_equivalent=true`：主比较不显著不构成等效证据。
- 仅在正式结局访问前可启用（`enable_only_before_formal_outcome_access=true`）。

## 6. 缺失数据处理（Missingness）

| 规则 | 规格 |
|---|---|
| 分离 | affect 与 sensor 缺失分开处理（`affect_and_sensor_separated=true`） |
| sensor 失败 | 不丢弃有效 PANAS（`sensor_failure_does_not_drop_valid_panas=true`） |
| 插补 | candidate_imputations=100（候选值，待冻结） |
| 机制网格 | model_and_mnar_grid=null（UNFROZEN，待 SAP_FREEZE_REQUIRED） |
| 状态 | **SAP_FREEZE_REQUIRED**：正式冻结前需完成 missingness 与 MNAR 网格设计 |

## 7. 样本规划（Sample Planning）

| 锚点 | 值 | 含义 |
|---|---|---|
| level_c_anchor | 48 | 每臂平衡序列数锚点（candidate） |
| stage_1_old_complete_target | 192 | 旧完成目标（非最终功效锚点） |
| stage_1_old_recruitment_cap | 240 | 旧招募上限（非最终） |
| formal_randomized_n | null（UNFROZEN） | 正式随机化 N，待真实冻结 |
| formal_recruitment_cap | null（UNFROZEN） | 正式招募上限，待真实冻结 |
| main_power_target_candidate | 0.9 | 主功效目标候选（0.9） |
| old_anchors_are_not_final_power | true | 旧锚点不构成最终功效声明 |
| equivalence_power_not_claimed | true | 不声明等效功效 |

- **N 与效应值不写死**：功效模拟以 N × 效应网格输出，由真实冻结决定最终 N。

## 8. 序列与随机化（Sequence & Randomization）

- stage_1 每臂平衡序列数 = 24（`stage_1_balanced_sequences_per_arm=24`）。
- 分配块大小候选 = 48（`allocation_block_size_candidate=48`）。
- 平衡单元 = 已分配而非已完成（`balance_unit=assigned_not_complete`）。
- 禁止基于完成的补位（`completion_based_refilling_forbidden=true`）。
- 禁止基于结局的可选停止（`outcome_based_optional_stopping_forbidden=true`）。

## 9. 运行时契约（Formal Runtime）

- Python 为权威实现（`python_is_authority=true`）；Unity 与 TD 独立（`unity_independent_of_td=true`）。
- 禁止 spout、禁止 mock（`spout_forbidden=true` / `mock_forbidden=true`）。
- 遥测 20Hz（`telemetry_hz=20`）；runtime_contract_version=2.2。
- 正式运行要求 live_e2e（`live_e2e_required=true`）。

## 10. 声明边界（Claim Boundaries）

以下声明**一律不主张**（全部 false）：

- 全项目因果效应、独立天气效应、独立呼吸结构效应、单一视觉机制效应、长期效应、短期 vs 长期交互，以及超出本项目交互状态估计范围的效果。

## 11. 需要正式冻结的条目（Required Freezes，15 项）

本 SAP 不执行正式冻结。与 U12-04 直接相关的冻结条目及其当前状态：

| # | 冻结条目 | 当前状态 |
|---|---|---|
| 1 | panas_version_and_permission | UNFROZEN（待工具冻结任务） |
| 2 | eligibility_and_recruitment | UNFROZEN（待招募冻结任务） |
| 3 | training_budget | UNFROZEN（U12-03/U12-11 协同 X-01 冻结） |
| 4 | randomization_and_concealment | UNFROZEN（待随机化冻结任务） |
| 5 | minimum_important_affect_difference | **UNFROZEN（本 SAP 保持 null）** |
| 6 | missingness_and_mnar | **UNFROZEN（SAP_FREEZE_REQUIRED）** |
| 7 | functional_margin_justification | **UNFROZEN（0.075 为继承候选）** |
| 8 | critical_error_thresholds | UNFROZEN |
| 9 | final_power_and_n | **UNFROZEN（本 SAP 输出网格，不冻结单点）** |
| 10 | stopping_rule | UNFROZEN（禁止结局可选停止） |
| 11 | institutional_scope | UNFROZEN |
| 12 | live_e2e | UNFROZEN |
| 13 | runtime_gate_integration | UNFROZEN |
| 14 | data_retention_and_access | UNFROZEN |
| 15 | pretreatment_baseline_and_condition_training_order | UNFROZEN |

## 12. 结论边界

- 本 SAP 是统计规格候选，证据类别为 DESIGN_AND_SYNTHETIC_ONLY。
- 功效模拟使用合成数据推演，不构成真实功效或正式 N 声明（`old_anchors_are_not_final_power=true`）。
- 正式冻结须由真实第二人独立复核并签收（见 U12-04 TASK.md AC3）。
- 历史 DONE 制品（U12-01、F-02 等）不被本任务改写。
