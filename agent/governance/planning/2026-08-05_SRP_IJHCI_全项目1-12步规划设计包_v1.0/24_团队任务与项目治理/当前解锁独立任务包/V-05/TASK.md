# V-05 【Unity预制作】四模块全旅程灰盒与形成性回退门

## 2026-10-08 当前实施补充

以[当前任务执行范围](../../../../../../tasks/V-05/TASK.md)的新基线为准：固定开环A对原生受限适应B，共同I与下发G/实际X分离；Storm与粒子资产、Unity2022.3.62f3保留。
原领取inputs和候选身份保留；design_updates/是显式新增设计要求，见FILES与manifest。原签收不转移，新范围AC与证据全部待实际验证。

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：未领取
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：未指定
- 领取时间：未领取

## 任务边界

- 领域：Unity预制作
- 波次：W2
- 状态：`READY`
- 类型：FIXED
- 预计工作量：5人日
- 前置依赖：F-03、U-02、V-04
- 所需技能：Unity灰盒+DEV-REPLAY+流程验证+形成性评审
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)
- [L-RESEARCH 中国大学MOOC研究方法课程检索入口](https://www.icourse163.org/search.htm?search=%E7%A0%94%E7%A9%B6%E6%96%B9%E6%B3%95)

## 交付物

- 固定/受限适应全旅程灰盒修订交接
- 新灰盒录像
- 时序与异常报告

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1 DEV-REPLAY分别核对A输入隔离和B合法边界调整
- [ ] AC2 同预算覆盖慢半步、漏补吸、低质量、恢复、模块末尾
- [ ] AC3 形成性问题真实关闭，旧48组合不证明新控制与用户理解

## 必需证据

- [ ] 新灰盒录像
- [ ] 时序与异常报告
- [ ] 评审问题关闭矩阵

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
