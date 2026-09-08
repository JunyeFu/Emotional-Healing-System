# U12-02 【测量实现】步骤实例测量与实际未知负测试

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex
- 分支：`codex/u12-02-step-measurement`
- 第二复核人：独立Agent复核；真实第二人签收另记
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：测量实现
- 波次：W1
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：U12-01、F-02、F-05
- 所需技能：Python+统计复算+合同测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-STAT Datawhale统计学习方法解答](https://datawhalechina.github.io/statistical-learning-method-solutions-manual/)
- [L-PYTEST pytest中文文档](https://pytest.cn/en/stable/)

## 交付物

- 题库与答案生成器
- 独立标注计划
- 负例

## 四阶段过程

1. 锁定输入层、算法版本、种子和预期fixture。
2. 实现确定性处理、模型或决策逻辑。
3. 运行边界、缺失、敏感性和重放验证。
4. 输出可复现报告、哈希、结论边界和交接数据。

## 验收要求

- [x] AC1按冻结输入完成交付，版本与来源可追溯
- [x] AC2hold_1/hold_2和inhale_1/inhale_2可区分
- [x] 实际null不借目标补值
- [ ] AC3证据与提交绑定，经独立复核及真实第二人签收，不代签外部条件 — `PENDING_HUMAN_SIGNOFF`

## 必需证据

- [x] 输入与交付哈希
- [x] 专项验证或外部回执
- [x] 独立复核记录

## 完成条件

新制品验收对象明确；不覆盖历史DONE；研究证据单独判断

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PASS`
- 证据路径：
- commit：`ba495b54e6939c2bb1c4a07592400f82c0292864`
- push目标：`origin/codex/u12-02-step-measurement`
- 真实团队第二人复核：`PENDING`
- 剩余风险：傅钧烨签收仍开放；任务文档列明的外部边界仍开放
