# U12-04 【统计规格】PANAS主结果SAP与新功效规格

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex(Grip)/小彬
- 分支：`codex/u12-04-panas-sap`
- 第二复核人：未指定
- 领取时间：2026-09-20

## 任务边界

- 领域：统计规格
- 波次：W1
- 状态：`IN_PROGRESS`（交付完成，待第二复核人签收）
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：U12-01、F-02
- 所需技能：Python+统计复算+合同测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-STAT Datawhale统计学习方法解答](https://datawhalechina.github.io/statistical-learning-method-solutions-manual/)
- [L-PYTEST pytest中文文档](https://pytest.cn/en/stable/)

## 交付物

- SAP
- 差值方向
- 参数来源
- 功效模拟规格

## 四阶段过程

1. 锁定输入层、算法版本、种子和预期fixture。
2. 实现确定性处理、模型或决策逻辑。
3. 运行边界、缺失、敏感性和重放验证。
4. 输出可复现报告、哈希、结论边界和交接数据。

## 验收要求

- [x] AC1按冻结输入完成交付，版本与来源可追溯（input_snapshot_id=236F924514D791AE5506457027E2598CE5C27B29F6A0CE39101F3262142843C3，sources 7/7 哈希 verified）
- [x] AC2双侧主比较（test_contract.py 双向 P 值测试通过）
- [x] 等效默认不启用（equivalence.confirmatory_enabled=false 契约保持）
- [x] N和界值待真实冻结（formal_randomized_n=null、margin_candidate=0.075，未伪造冻结）
- [x] 覆盖正反零与缺失情景（pytest 18 passed 含 negative/zero/missing 用例）
- [ ] AC3证据与提交绑定，经独立复核及真实第二人签收，不代签外部条件（第二复核人未指定，待真实签收）

## 必需证据

- [x] 输入与交付哈希（evidence.json：input_snapshot_id、baseline_commit、sources 7 verified、outputs 9 verified）
- [x] 专项验证或外部回执（validate.py PASS / pytest 18 passed / POWER_GRID_OK cells=20 / EVIDENCE_OK）
- [x] 独立复核记录（见 `U12-04独立复核记录.md`；真实第二人签收仍待完成）

## 完成条件

新制品验收对象明确；不覆盖历史DONE；研究证据单独判断

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件（交付目录 `../../u12_upgrade/U12-04_panas_sap/`）：
  - `sap.md`：PANAS 主结果 SAP（primary=stage_1/panas_negative_affect_post_adjusted_for_pre/native_minus_abstract/two_sided/alpha=0.05/HC3/lower_is_better=true）
  - `contract.json`：SAP 契约（functional_guard margin_candidate=0.075、equivalence confirmatory_enabled=false、missingness SAP_FREEZE_REQUIRED、sample_planning main_power_target_candidate=0.9、required_freezes 15 项）
  - `power_spec.json`：新功效模拟规格（双分析集 PRIMARY_CONSERVATIVE/OBSERVED_CASE；n_grid=[48,96,144,192,240]×effect_grid=[0.2,0.3,0.4,0.5]=20 cells）
  - `power_simulation.py`：确定性 Monte Carlo 功效模拟（seed=20260906、replications=1000、_ols_hc3 手动 HC3、_two_sided_p scipy t 分布）
  - `power_grid.json`：20 cells 功效网格结果；`power_report.md`：功效模拟报告
  - `sources.md`：输入快照与来源（7 项，hash_policy=sha256_lf_no_trailing_ws_text_v1）
  - `validate.py`：输入快照/基线/契约校验（修复 baseline_commit 假 PASS，兼容 task_input 的 base_commit 键）
  - `test_contract.py`：pytest 18 用例（正反零与缺失情景、双侧主比较保持、负向候选拒绝、required_freezes 存在）
  - `build_evidence.py`：证据构建（v1.0 解锁登记区 manifest 为输入权威 + v1.2 task_input base_commit）；`evidence.json`：证据文件
  - `README.md`：uv run --python 3.14.7 四步验证说明
- 验证命令与结果：
  - `uv run --python 3.14.7 python validate.py` → PASS（输入快照哈希 7/7、baseline_commit=de4ebcbfea209674127c833dd9e69ad703a6634b 匹配、required_freezes 15 项齐备、无契约变更）
  - `uv run --python 3.14.7 python -m pytest test_contract.py -q` → 18 passed in 0.06s
  - `uv run --python 3.14.7 python power_simulation.py --output-dir .` → POWER_GRID_OK（cells=20：n_grid 5 × effect_grid 4；replications=1000；seed=20260906 确定性）
  - `uv run --python 3.14.7 python build_evidence.py` → EVIDENCE_OK；`python build_evidence.py --check` → EVIDENCE_OK（sources 7/7 verified、outputs 9/9）
- 证据路径：`../../u12_upgrade/U12-04_panas_sap/evidence.json`（含 input_snapshot_id=236F9245…、baseline_commit=de4ebcbf…、sources/outputs 哈希）
- commit：772e61d（领取登记 IN_PROGRESS）；完成提交见本次 push 的 commit
- push目标：`origin/main`（分支 `codex/u12-04-panas-sap`，push origin HEAD:main；不覆盖历史 DONE）
- 剩余风险：
  - N 与 margin 界值未真实冻结（formal_randomized_n=null、margin_candidate=0.075）：按 missingness 契约 SAP_FREEZE_REQUIRED，等价检验 confirmatory_enabled=false 保持不启用
  - main_power_target_candidate=0.9 为候选值；真实数据（real_clips/participant_observations）到齐后需正式样本量复核
  - AC3 第二复核人未指定，需真实第二人签收，不代签外部条件
