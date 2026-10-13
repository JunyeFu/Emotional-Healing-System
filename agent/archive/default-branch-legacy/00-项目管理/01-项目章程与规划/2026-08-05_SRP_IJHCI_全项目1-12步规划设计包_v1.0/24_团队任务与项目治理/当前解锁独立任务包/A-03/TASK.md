# A-03 【统计实现】Gate2联合测量估计目标与Monte Carlo样本模拟

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex
- 分支：`codex/a-03-spec`
- 第二复核人：未指定
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

- PANAS与SCCI计分
- 四层理解与心智努力
- 序数项目和条件间差异
- Gate1至3估计目标表
- 阶段错误汇总
- 有界结果Monte Carlo

## 四阶段过程

1. 锁定输入层、算法版本、种子和预期fixture。
2. 实现确定性处理、模型或决策逻辑。
3. 运行边界、缺失、敏感性和重放验证。
4. 输出可复现报告、哈希、结论边界和交接数据。

## 验收要求

- [ ] AC1SCCI只作操纵检查且四层理解心智努力分别建模
- [ ] AC2项目差异FDR缺失与冻结原因码fixture通过
- [ ] AC3模拟覆盖上限效应两分析集同时通过差异性缺失和有序门并给出当前上限可行或NO_GO

## 必需证据

- [ ] 计分测试
- [ ] 估计目标表
- [ ] 测量报告模板
- [ ] Monte Carlo输出
- [ ] 固定种子复现

## 完成条件

许可和Level材料未确认时只使用合成fixture且不得以正态锚点替代最终模拟

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
