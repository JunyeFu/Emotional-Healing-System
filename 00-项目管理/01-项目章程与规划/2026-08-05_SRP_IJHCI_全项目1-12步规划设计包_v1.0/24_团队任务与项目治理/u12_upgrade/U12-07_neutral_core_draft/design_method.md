# U12-07 交付物 1：设计方法稿（结果前中立核心稿·方法部分候选）

> 任务：U12-07【论文写作】结果前中立核心稿与正反模板
> 状态：`PLANNED_NOT_OBSERVED` / 设计候选，非预注册、非已实现
> 版本：v0.1-candidate（阶段 2 产出，未经第二人复核）

## 0. 文件头声明（阶段 1：受众、输入、交付清单、公开限制）

### 0.1 目标受众

| 受众 | 使用方式 | 关注点 |
|---|---|---|
| 论文写作团队（W-01 后续执笔人） | 直接复用到论文"方法"与"结果前"部分的文字与表格 | 与锁定输入一致、可直接引用、不越界 |
| 项目 PI / 研究负责人 | 审阅方法与声明边界是否与协议权威一致 | 估计目标、Gate 结构、不主张清单 |
| IJHCI 审稿人（潜在读者） | 未来投稿后评估方法完整性与主张克制 | 中立表述、可复现性、失败边界 |

### 0.2 输入版本（6 锁定来源）

| 序号 | 输入 | 权威路径 | SHA-256（见 FILES.md） |
|---|---|---|---|
| 01 | protocol_authority_v1.2.json | `00_总控/protocol_authority_v1.2.json` | `3E5015BBA65588FF852E05B1831CB062E606F3ECB78C1F5B008FE61840D59DE6` |
| 02 | consumers.json | `24_团队任务与项目治理/u12_upgrade/consumers.json` | `2F68C3877531DB831C6CC4FDF22A0D039FA2491E988C4EFA8AA46A91C164A91E` |
| 03 | study_manifest_v1.2.template.json | `24_团队任务与项目治理/u12_upgrade/study_manifest_v1.2.template.json` | `43A720E65F10EB49818B3130143C57B7BF1DA106A312B9A9430603EC35DD088B` |
| 04 | release_routes_v1.2.json | `24_团队任务与项目治理/audit_upgrade/release_routes_v1.2.json` | `D9248B5EBE79EA40EB41A5CAD44DB0BF84BFB0A0EDAD085F8EC3192F37568331` |
| 05 | task_milestones_v1.2.json | `24_团队任务与项目治理/audit_upgrade/task_milestones_v1.2.json` | `D38328914584CDBBFA32601C89F3E50DD7A4D3A336930EBCD5A471CC7115BBA8` |
| 06 | task_input.json | `2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-07/inputs/task_input.json` | `302E8C641B6DD877852B9AD4F8E5A97990DA4640F5C73D3D737C90FB0089A2AE` |

另读取的写作输入（非锁定哈希来源，作为方法与内容上下文）：W-01 论文骨架 v0.9-candidate（`25_论文投稿与成果交付/W-01_最近工作与论文骨架/`）、R-01 四层表示方案 v0.9-candidate（`20_产品与场景设计/R-01_四层表示方案/`）、U12-04 证据格式参照（`u12_upgrade/U12-04_panas_sap/`）。

### 0.3 交付清单

| 交付物 | 文件 |
|---|---|
| 设计方法稿 | `design_method.md`（本文件） |
| 空表规格 | `empty_table_spec.md` |
| 正反结果句式 | `claim_sentences.md` |

### 0.4 公开限制

1. **不填造数据**：全部结果位置使用 `[占位]` 或"待观测"表述；不预填方向、不虚构数值、不根据设计推断效应。
2. **不等阶段三**：序列编排扩展仅以条件式占位出现，仅在 U6 与 Gate 3 均通过后进入主贡献；当前不得与主贡献并列。
3. **每类结果有准确边界**：结果报告按 Gate 顺序与主张—证据矩阵 C1–C6 的成立/降级规则逐类限定；禁止用总分掩盖层级、用体验补偿错误、用"未发现相同研究"证明新颖性。

---

## 1. 研究问题与估计目标

研究以"表示的功能—体验张力"为切入，比较两种**完整提示表示方案**（场景原生 `scene_native` 与抽象双环 `abstract_pacer`），不保证原生方案胜出（protocol_authority `research_question`：比较两种完整呼吸提示方案的短时状态性负性情绪结果、执行与负担，不保证原生胜出）。

四个研究问题（沿用 W-01 骨架，均为候选）：

- **RQ1**：场景原生完整提示表示方案能否先保持机会分母执行质量非劣，再在场景融合操纵成立时维持四层理解和心智努力？
- **RQ2**：两个完整方案在客观阶段错误、注意连续性、喜欢度、舒适度和目的猜测上有何差异？
- **RQ3**：四个固定复合实例的客观失败、正例和负例支持哪些有边界的设计规则？
- **RQ4**（条件式）：仅当 U6 通过时，冻结部署策略能否在独立队列中相对均衡随机顺序降低体验后 PANAS 负性维度并保持执行护栏？

估计目标（protocol_authority）：

| 目标 | 定义 | 关键参数（候选/待冻结） |
|---|---|---|
| 功能护栏（Gate 1） | 机会分母参与者协议保真度，`native_minus_abstract` 非劣 | 非劣界 `0.075`（`INHERITED_REQUIRES_JUSTIFICATION`，须冻结论证）；分析集 `all_randomized` + `complete_four_module`，两者均须通过才可主张原生替代 |
| 操纵检查（SCCI） | `manipulation_only`；单独不使随机化比较失效、不阻断预指定结果报告 | 项目自建操纵检查，须在局限中声明 |
| 四层理解 | 条件中性理解测验（八题，0–8） | 理解和努力界值仍为候选，须在查看正式条件差前按 Level A/B 与 Level C 盲态参数冻结 |
| 心智努力 | 组间差、区间与非劣结论 | 同上 |
| 客观阶段错误护栏 | 阶段错误客观测量 | `critical_module_error_thresholds` 当前 `null`，须冻结 |

主结果（protocol_authority `primary`）：`panas_negative_affect_post_adjusted_for_pre`，对比 `native_minus_abstract`，双侧检验，`alpha=0.05`，候选模型 `NA_post ~ cue_mode + centered_NA_pre + randomization_strata`，HC3 方差。功能护栏失败也照常报告（`report_even_if_functional_guard_fails: true`）。

样本规划（`sample_planning`）：Level C 锚点 48；阶段一旧完整目标 192（每方案 96）、旧招募上限 240；主功效目标候选 0.9；旧锚点不是最终功效，须在 Level C 后用盲态方差、缺失、上限效应与联合通过率做 Monte Carlo 模拟后冻结 `formal_randomized_n` 与 `formal_recruitment_cap`。

---

## 2. 两完整提示表示方案定义

两种方案都定义为**完整方案**（`conditions.treatment = complete_cue_representation_package`），而非单机制差异。

**共享成分**（两方案相同）：事件真值、时长（`core_experience`：demo 25s、closed_loop 150s、lock_transition 25s，共 4 模块，推荐总时长 800s）、目标结构、实际输入（`python.interaction_state_estimate`）、累计函数（`python.recovery_aggregate`）、降级原因（`python.signal_quality`）、音频、场景。

**完整方案差异**（仅目标与实际信息的表示组织不同）：

| 维度 | `scene_native` | `abstract_pacer` |
|---|---|---|
| 目标表示 | 场景自身机制表达目标阶段与转换（`scene_far_field`/`scene_near_field`/`scene_actual_channel_attenuation`） | 外环表达目标（`abstract_outer_ring`） |
| 实际表示 | 场景自身表达当前被观察到的执行（`scene_actual_channel`） | 内环表达实际（`abstract_inner_ring`，`inner_ring_attenuation`） |
| 累计表示 | 共享场景慢变量（`cumulative_presentation = shared_scene_slow_variable`） | 同左 |
| 降级表示 | 质量状态与原因（`fallback_presentation`） | 同左 |

两条件共享同一参与者说明、SCCI、理解题与问卷预算；颜色不是唯一通道（`color_is_not_sole_channel=true`，WCAG 2.2 SC 1.4.1/1.4.11、2.3.1 作为设计依据之一）。

---

## 3. 四层候选设计合同

候选四层语法（R-01 v0.9-candidate，`status=CANDIDATE`、`evidence_status=PLANNED_NOT_OBSERVED`、`provenance.review_status=NOT_DUAL_REVIEWED`）：

| 层 | 输入源 | 表示职责 | 禁止耦合 |
|---|---|---|---|
| 目标 | `python.target_protocol`（`target_phase`/`target_progress`），语义 prescriptive，平滑 ≤250ms | 告诉参与者当前应跟随的阶段及转换 | 不由当前表现或奖励反向改变 |
| 实际 | `python.interaction_state_estimate`（`actual_phase`/`actual_progress`/`actual_confidence`），语义 descriptive，平滑 ≤500ms | 表达当前被系统可靠观察到的执行 | 不伪装成目标，不以零值代替缺失 |
| 累计 | `python.recovery_aggregate`（`recovery_value`/`recovery_locked`），语义 module_to_date，视觉时间常数 2–10s | 概括一段过程而非当前瞬间 | 不与某一瞬时错误同义，不在数据不可用时继续美化 |
| 降级 | `python.signal_quality`（`signal_quality`/`fallback_state`/`fallback_reason`），语义 epistemic + display policy | 表达部分当前信息可信度下降 | 不评价参与者能力（`participant_blame_forbidden=true`），不改变固定目标协议 |

**降级四态契约**（`fallback_contract`）：

| 状态 | 实际通道 | 累计通道 | 禁止 |
|---|---|---|---|
| `GOOD` | continue / real / update | 正常更新 | — |
| `DEGRADED` | continue / attenuate / pause 或 cautious_update | 谨慎更新 | 平滑跨越长断流 |
| `UNUSABLE` | stop（实际=停止） | pause（累计=暂停） | 禁止 Mock 填补、禁止为保持画面美观继续恢复 |
| `DISCONNECTED` | safe_open_loop 或 abort / stop / pause | 暂停 | 不伪造信号 |

**层级耦合与加载约束（四类负例）**：
1. 缺字段负例：缺失 `layers.fallback` 等必需字段时拒绝加载，不得静默补齐。
2. 层级耦合负例：`actual.source` 必须为 `python.interaction_state_estimate`，防止用目标动画伪装实际反馈。
3. 非法降级负例：`UNUSABLE` 必须满足 actual=stop 与 cumulative=pause 语义，禁止 Mock 填补或为美观继续恢复。
4. 越界混杂负例：六类混杂任一越界即不得进入 Level 材料构建；无法修正时记录为不可消除的完整方案差异，而非反复调整阈值。

---

## 4. 参与者说明候选（条件中性）

参与者说明候选全文（用于阶段一；措辞保持条件中性，不出现"天气融合""场景原生更自然""圆环更清楚"等偏好暗示）：

- 说明将体验两种完整提示表示方案之一；说明画面会随时间显示四类功能信息——目标阶段、实际执行、模块累计、以及信息可信度下降时的降级语义。
- 说明出现降级时，信息呈现会受限或暂停，这是系统的诚实表达，不是参与者的错误。
- SCCI 安排在 PANAS 后测之后，避免操纵检查本身成为新的干预事件。
- 正式训练预算（`training.budget_seconds`）当前为 `null`，`mode=EQUAL_FINITE_BUDGET_PROPOSED`；条件特定训练在 PANAS 前测之后进行（`condition_specific_training_after_panas_pre=true`），该时序须在冻结训练预算时一并确认（`required_freezes.training_budget`、`pretreatment_baseline_and_condition_training_order`）。

---

## 5. SCCI 操纵检查角色

- 工具：SCCI（项目自建操纵检查，`manipulation_check.instrument=SCCI`）。
- 角色：仅作操纵检查（`role=manipulation_only`）；单独失败不使随机化比较无效（`failure_alone_invalidates_randomized_comparison=false`）；不阻断预指定结果报告（`blocks_prespecified_outcome_reporting=false`）。
- 报告位置：在结果中按 SCCI 项目分布、序数分析、条件间项目功能差异报告；若出现无法解释的跨条件项目功能差异，作为 R-01 失败模式之一处理（见正反句式，禁用 SCCI 总分补偿）。
- 引用支撑：操纵检查的反应性风险参考 Hauser, Ellsworth & Gonzalez (2018, Front. Psychol., DOI 10.3389/fpsyg.2018.00998)——注意本文 SCCI 本身可能具有反应性，须在局限中说明。

---

## 6. 四层理解八题矩阵（F-02 接口）

理解测验共八题，覆盖四层，每层两题；每题 0/1 计分，总分 0–8，每层 0–2；作答状态区分 `RESPONDED` / `SKIPPED` / `TIMEOUT` / `TECH_UNPRESENTED`。

| 题号 | 层 | 题目功能 | 必须可见信息 | 两条件等值要求 |
|---|---|---|---|---|
| C-T1 | 目标 | 识别片段结束时目标阶段 | 目标阶段事件真值 | 题目可仅依据目标信息作答 |
| C-T2 | 目标 | 推断仅依据目标信息的下一步 | 目标阶段与转换真值 | 目标信息在两条件同等可见 |
| C-A1 | 实际 | 识别当前实际阶段 | 实际阶段事件真值 | 实际信息在两条件同等可见 |
| C-A2 | 实际 | 判断实际相对目标的关系 | 实际与目标事件真值 | 关系可仅依据两通道作答 |
| C-C1 | 累计 | 识别累计信息的时间范围=module_to_date | 累计函数语义 | 累计呈现方式两条件一致 |
| C-C2 | 累计 | 区分瞬时与累计信息 | 瞬时/累计标签语义 | 区分能力不受表示组织影响 |
| C-D1 | 降级 | 理解信息受限的含义 | 降级状态与原因 | 降级语义两条件一致 |
| C-D2 | 降级 | 识别受影响的信息类别 | 降级影响范围 | 受影响类别两条件一致 |

每题还须满足：正确答案生成规则、片段失效条件（如 `TECH_UNPRESENTED`）在 F-02 中定义；本稿不展开题目原文，仅锁定矩阵接口。构念交叉污染检查（目标/实际/累计/降级/SCCI/四层理解/心智努力/事件显著度/累计奖励/降级恢复）在 R-01 中定义，作为理解题效度检查项。

---

## 7. 六类视觉混杂预算

两条件作为完整方案差异，混杂审计的目标是发现**致命失衡**，不是证明两个画面物理相同。六类候选上限（`evidence_label=ENGINEERING_CANDIDATE`、`freeze_status=PENDING_LIVE_MEASUREMENT`，须在正式条件差揭示前冻结）：

| 混杂维度 | 候选上限 | 单位/方向 | 越界处置 |
|---|---|---|---|
| 运动能量相对差 | ≤ 0.10 | 相对 | 不得进入 Level 材料构建 |
| 平均亮度绝对差 | ≤ 0.05 | 绝对 | 同左 |
| 视觉复杂度相对差 | ≤ 0.10 | 相对 | 同左 |
| 空间偏心差 | ≤ 2.0 | 度 | 同左 |
| 遮挡绝对差 | ≤ 0.03 | 绝对 | 同左 |
| 事件显著度相对差 | ≤ 0.15 | 相对 | 同左 |

无法修正时，记录为不可消除的完整方案差异并转入失败模式处理（正反句式中有对应降级句式），不得反复调整阈值直到"看起来通过"。

---

## 8. 失败模式与主张降级（写作约束摘要）

完整 12 行失败模式表与 6 种可推翻强主张模式见 R-01 与正反句式交付物；本稿仅锁定方法侧约束：

1. 结果必须按门控顺序呈现（样本流 → 实现与混杂 → Gate 1 → SCCI → 四层理解 → 心智努力 → 联合 Gate 2 → 次要家族 → 独立重建 → 四场景知识 → 序列扩展（条件）→ 敏感性）。
2. 总理解分数满足不得掩盖关键层失败；喜欢度提高不得补偿客观阶段错误。
3. 独立重建未通过时全文统一降称"四场景设计模式"，不得写"证明了通用四层框架"。
4. Gate 2 失败时，把负结果、冲突与失败规则作为主要知识输出。
5. 序列编排仅可在 U6 与 Gate 3 均通过后与主贡献并列；否则只能放在未来工作或补充方法。

---

## 9. 声明边界（全部不主张）

（protocol_authority `claim_boundaries` 全部为 false，投稿时不得反向主张）

| 不主张项 | 含义 |
|---|---|
| 整项目因果效应 | 不把全流程效果归因于单一系统环节 |
| 独立天气效应 | 不把"天气/场景"当作独立变量 |
| 独立呼吸结构效应 | 不把呼吸结构当作独立变量 |
| 单一视觉机制效应 | 不做单机制归因 |
| 长期效应 | 不主张长期效果 |
| 短长交互 | 不主张短时—长期交互 |
| 诊断或治疗功效 | 不主张任何疗效 |

---

## 10. 复现与可审计运行（方法侧承诺）

- Python 是会话、单调时钟、目标相位、交互状态估计、质量、累计状态与落盘的唯一权威；Unity 是参与者唯一渲染制品；TD 为只读操作台（`formal_runtime`：`spout_forbidden=true`、`mock_forbidden=true`、`telemetry_hz=20`、`runtime_contract_version=2.2`、`live_e2e_required=true`）。
- 正式 Unity 不得依赖 TD 或 Spout；缺失测量使用空值与原因码，不得用 Mock 或零值替代。
- 系统证据报告项：构建/配置/随机化清单哈希、双设备真实会话与故障注入、控制事件 ACK 与幂等性、外部端到端呈现延迟、四态降级行为、L0–L5 可重建性、干净机器复现与环境锁。
- 证据类：`DESIGN_AND_SYNTHETIC_ONLY`（本阶段）；`real_clips`、`participant_observations`、`research_freeze` 均 `PENDING`。