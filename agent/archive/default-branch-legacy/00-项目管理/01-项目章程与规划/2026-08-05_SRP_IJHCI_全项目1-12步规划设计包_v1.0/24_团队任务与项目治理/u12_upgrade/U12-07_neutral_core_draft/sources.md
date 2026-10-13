# U12-07 证据来源表（sources.md）

> 任务：U12-07【论文写作】结果前中立核心稿与正反模板
> 状态：`PLANNED_NOT_OBSERVED` / 设计候选，非预注册、非已实现
> 输入快照：`F816769755011E0A4AAE28ADD0DA96548B70CE0A1EB3A8F1AC29E1F7F25FBD9A`
> 基线提交：`de4ebcbfea209674127c833dd9e69ad703a6634b`
> 本表对应 evidence.json 的 sources 六项；全部 `verified: true`（原始字节 SHA-256 与 package_manifest.json 声明一致，本阶段已重算验证）。

## 锁定输入版本（0.2 表与 FILES.md 一致）

| 参数 | 值 | 来源 |
|---|---|---|
| 输入快照 ID | `F816769755011E0A4AAE28ADD0DA96548B70CE0A1EB3A8F1AC29E1F7F25FBD9A` | `当前解锁独立任务包/U12-07/package_manifest.json` |
| 基线提交 | `de4ebcbfea209674127c833dd9e69ad703a6634b` | `study_manifest_v1.2.template.json` `adaptation_base_commit` |
| 01 protocol_authority_v1.2.json | SHA-256 `3E5015BBA65588FF852E05B1831CB062E606F3ECB78C1F5B008FE61840D59DE6` | `00_总控/protocol_authority_v1.2.json` |
| 02 consumers.json | SHA-256 `2F68C3877531DB831C6CC4FDF22A0D039FA2491E988C4EFA8AA46A91C164A91E` | `24_团队任务与项目治理/u12_upgrade/consumers.json` |
| 03 study_manifest_v1.2.template.json | SHA-256 `43A720E65F10EB49818B3130143C57B7BF1DA106A312B9A9430603EC35DD088B` | `24_团队任务与项目治理/u12_upgrade/study_manifest_v1.2.template.json` |
| 04 release_routes_v1.2.json | SHA-256 `D9248B5EBE79EA40EB41A5CAD44DB0BF84BFB0A0EDAD085F8EC3192F37568331` | `24_团队任务与项目治理/audit_upgrade/release_routes_v1.2.json` |
| 05 task_milestones_v1.2.json | SHA-256 `D38328914584CDBBFA32601C89F3E50DD7A4D3A336930EBCD5A471CC7115BBA8` | `24_团队任务与项目治理/audit_upgrade/task_milestones_v1.2.json` |
| 06 task_input.json | SHA-256 `302E8C641B6DD877852B9AD4F8E5A97990DA4640F5C73D3D737C90FB0089A2AE` | `2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-07/inputs/task_input.json` |

## 研究问题与估计目标来源

| 参数 | 值 | 来源 |
|---|---|---|
| 不保证原生胜出 | `research_question`：比较两种完整呼吸提示方案，不保证原生胜出 | protocol_authority_v1.2.json |
| 主结果 | `panas_negative_affect_post_adjusted_for_pre`，`native_minus_abstract`，双侧 0.05，候选模型 `NA_post ~ cue_mode + centered_NA_pre + randomization_strata`，HC3 | protocol_authority_v1.2.json `primary` |
| 功能护栏 | 非劣界 `0.075`（`INHERITED_REQUIRES_JUSTIFICATION`）；分析集 `all_randomized` + `complete_four_module` 两者均须通过；护栏失败照常报告 | protocol_authority_v1.2.json `functional_guard` |
| 操纵检查 | SCCI `manipulation_only`；单独失败不使随机化比较无效、不阻断报告 | protocol_authority_v1.2.json `manipulation_check` |
| 等效性 | `confirmatory_enabled=false`、`not_significant_is_not_equivalent=true` | protocol_authority_v1.2.json `equivalence` |
| 缺失 | 插补 100；情绪与传感器分离 | protocol_authority_v1.2.json `missingness` |
| 样本规划 | Level C 锚点 48；阶段一旧完整目标 192、旧上限 240；主功效目标候选 0.9；旧锚点非最终功效 | protocol_authority_v1.2.json `sample_planning` |
| 序列 | 阶段一每臂 24 平衡序列；分配块候选 48；以分配非完成平衡；禁止按完成补填；禁止按结果可选停止 | protocol_authority_v1.2.json `sequence` |
| 阶段 2/3 | 最小均匀混合候选 0.2；均匀回退不构成策略优效证据；保留分组交叉拟合 | protocol_authority_v1.2.json `stage_2_3` |
| 运行时契约 | Python 权威；Unity 独立于 TD；禁 Spout、禁 Mock；遥测 20Hz；契约 2.2；live_e2e 必选 | protocol_authority_v1.2.json `formal_runtime` |
| 声明边界 | 全部不主张（整项目/独立天气/独立呼吸结构/单一视觉机制/长期/短长交互/诊断治疗） | protocol_authority_v1.2.json `claim_boundaries` |
| 待冻结 15 项 | `required_freezes` | protocol_authority_v1.2.json |
| 状态 | `DESIGN_CANDIDATE_NOT_PREREGISTERED` | protocol_authority_v1.2.json `status` |

## 研究清单与适配包来源

| 参数 | 值 | 来源 |
|---|---|---|
| 文档类型 | `UNFILLED_TEMPLATE_NOT_APPROVAL`（未批准模板） | study_manifest_v1.2.template.json `document_type` |
| 正式采集 | `formal_collection_allowed=false` | study_manifest_v1.2.template.json |
| 功能边际 | `0.075` | study_manifest_v1.2.template.json `functional_margin` |
| 采用状态 | `CANDIDATE_NOT_ACTIVE` | study_manifest_v1.2.template.json `adoption_status` |
| 消费者 | 论文写作团队 / PI / IJHCI 审稿人 | consumers.json |
| 发布路径与里程碑 | 结果占位 12 节与 U12-07 四阶段过程 | release_routes_v1.2.json / task_milestones_v1.2.json |
| 任务定义 | wave=W2、domain=论文写作、depends_on=U12-01\|W-01、effort=3人日、deliverables=设计方法稿;空表规格;正反结果句式、acceptance=不填造数据；不等阶段三；每类结果有准确边界、source_id=UP-07 | task_input.json |

## 写作上下文来源（非锁定哈希，方法内容上下文）

| 参数 | 值 | 来源 |
|---|---|---|
| 论文骨架 | W-01 结果占位 12 节与可推翻主贡献 10 行模式 | `25_论文投稿与成果交付/W-01_最近工作与论文骨架/`（v0.9-candidate） |
| 四层方案 | 目标—实际—累计—降级候选语法、降级四态、四类负例 | `20_产品与场景设计/R-01_四层表示方案/`（v0.9-candidate） |
| 证据格式参照 | evidence.json schema、sources.md 参数来源表格式 | `u12_upgrade/U12-04_panas_sap/` |
| 操纵检查反应性 | Hauser, Ellsworth & Gonzalez (2018, Front. Psychol., DOI 10.3389/fpsyg.2018.00998) | design_method.md §5 / claim_sentences.md 第 17 类 |

## 交付物与验收对应

| 交付物 | 文件 | 对应 AC |
|---|---|---|
| 设计方法稿 | `design_method.md` | AC1 输入版本与来源可追溯；AC2 不填造/不等阶段三/每类结果有准确边界 |
| 空表规格 | `empty_table_spec.md` | AC2 每类结果占位表与门控判定 |
| 正反结果句式 | `claim_sentences.md` | AC2 每类结果正反句式与降级规则；AC3 写作检查清单输入 |
| 证据来源表 | `sources.md`（本文件） | AC1 来源可追溯 |

## 复核与签收

| 项 | 状态 | 说明 |
|---|---|---|
| 第一复核（本阶段自检） | 完成 | 阶段 3：匿名、许可、复现、主张、完整性检查；6 输入快照哈希全部重算验证 `verified: true` |
| 第二人复核 | `PENDING` | 按治理流程由独立第二人复核并真实签收（不代签），冻结版本与移交记录 |
| research_freeze | `PENDING` | 正式条件差揭示前须冻结界值/训练预算等 15 项 |