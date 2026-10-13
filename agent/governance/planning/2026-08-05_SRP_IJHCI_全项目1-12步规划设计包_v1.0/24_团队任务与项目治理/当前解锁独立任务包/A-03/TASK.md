# A-03 【统计实现】Gate2联合测量估计目标与Monte Carlo样本模拟

## 2026-10-08 当前实施补充

以[当前任务执行范围](../../../../../../tasks/A-03/TASK.md)的新基线为准：固定开环A对原生受限适应B，共同I与下发G/实际X分离；Storm与粒子资产、Unity2022.3.62f3保留。
原领取inputs和候选身份保留；design_updates/是显式新增设计要求，见FILES与manifest。原签收不转移，新范围AC与证据全部待实际验证。

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex
- 分支：`codex/a-03-spec`
- 第二复核人：傅钧烨（团队总监，独立第二人复核）
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：统计实现
- 波次：W2
- 状态：`IN_PROGRESS`
- 类型：FIXED
- 预计工作量：5人日
- 前置依赖：F-02
- 所需技能：问卷计分+序数项目+估计目标+功效模拟
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-STAT Datawhale统计学习方法解答](https://datawhalechina.github.io/statistical-learning-method-solutions-manual/)
- [L-PANDAS Datawhale Joyful Pandas](https://github.com/datawhalechina/joyful-pandas)

## 交付物

- 新整包比较SAP与样本精度修订交接
- 新SAP修订差异
- 功效/精度情景

## 四阶段过程

1. 锁定输入层、算法版本、种子和预期fixture。
2. 实现确定性处理、模型或决策逻辑。
3. 运行边界、缺失、敏感性和重放验证。
4. 输出可复现报告、哈希、结论边界和交接数据。

## 验收要求

- [ ] AC1 重算PANAS-NA基线校正比较的新条件精度
- [ ] AC2 I/G执行分离，功能代价界及缺失需独立依据
- [ ] AC3 SPEC原签收保持，REAL/CAL与正式参数仍需真实材料

## 必需证据

- [ ] 新SAP修订差异
- [ ] 功效/精度情景
- [ ] 真实校准输入要求

## 完成条件

新范围由实际执行者取得上述证据及独立复核；历史DONE只覆盖原范围，本轮任务体系更新不转为新业务验收。

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
