# U12-07 【论文写作】结果前中立核心稿与正反模板

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex(Grip)/小彬
- 分支：`codex/u12-07-neutral-core-draft`
- 第二复核人：未指定
- 领取时间：2026-09-21

## 任务边界

- 领域：论文写作
- 波次：W2
- 状态：`IN_PROGRESS`（阶段1-3已完成，阶段4第二复核待安排）
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：U12-01、W-01
- 所需技能：研究设计+版本治理+证据审查
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-RESEARCH 中国大学MOOC研究方法课程检索入口](https://www.icourse163.org/search.htm?search=%E7%A0%94%E7%A9%B6%E6%96%B9%E6%B3%95)
- [L-MARKDOWN 菜鸟教程Markdown教程](https://www.runoob.com/markdown/md-tutorial.html)

## 交付物

- 设计方法稿
- 空表规格
- 正反结果句式

## 四阶段过程

1. 列出目标受众、输入版本、交付清单和公开限制。
2. 从锁定来源生成文稿、构建或归档候选。
3. 执行匿名、许可、复现、主张和完整性检查。
4. 由第二人复核并冻结版本、哈希和移交记录。

## 验收要求

- [x] AC1按冻结输入完成交付，版本与来源可追溯
- [x] AC2不填造数据
- [x] 不等阶段三
- [x] 每类结果有准确边界
- [ ] AC3证据与提交绑定，经独立复核及真实第二人签收，不代签外部条件

## 必需证据

- [x] 输入与交付哈希
- [x] 专项验证或外部回执
- [ ] 独立复核记录（第二复核人真实签收，待安排）

## 完成条件

新制品验收对象明确；不覆盖历史DONE；研究证据单独判断

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
  - 新增交付目录 `24_团队任务与项目治理/u12_upgrade/U12-07_neutral_core_draft/`：`design_method.md`（16,285B）、`empty_table_spec.md`（10,156B）、`claim_sentences.md`（12,909B）、`evidence.json`、`sources.md`（6,690B）
  - 本文件（TASK.md）完成回填
- 验证命令与结果：
  - PowerShell 原始字节 SHA-256 重算：6 个输入快照与 `package_manifest.json` 声明 6/6 完全一致（01=3E5015BB…、02=2F68C387…、03=43A720E6…、04=D9248B5E…、05=D3832891…、06=302E8C64…），`evidence.json` sources 全部 `verified:true`
  - 阶段3检查：按 `claim_sentences.md` 附写作检查清单 8 项逐项核验全部通过；匿名（无个人信息）、许可（Hauser et al. 2018 DOI 10.3389/fpsyg.2018.00998 保留）、复现（design_method.md §10 运行时契约完整）、主张（声明边界 7 项不主张）、完整性（0.2 表与 FILES.md 一致）
  - `evidence.json` JSON 解析校验通过（6 sources、4 outputs）
- 证据路径：`24_团队任务与项目治理/u12_upgrade/U12-07_neutral_core_draft/evidence.json`、`sources.md`
- commit：`f90688d`（领取登记）、`672b294`（交付物+证据）、（TASK.md 回填提交）
- push目标：`origin/main`
- 剩余风险：
  - AC3 第二复核人未指定，独立复核与真实签收待治理流程安排，不代签
  - `research_freeze` 15 项（界值/训练预算等）在正式条件差揭示前须冻结，`evidence.json` 尾项 `real_clips/participant_observations/research_freeze` 均 `PENDING`
  - 本包仅含 DESIGN_AND_SYNTHETIC_ONLY 设计候选，不构成预注册或正式结果