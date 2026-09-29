# U12-02【测量实现】步骤实例测量与实际未知

## 状态与责任

DONE，3人日，依赖U12-01/F-02/F-05。原领取人Codex、分支codex/u12-02-step-measurement；Carson独立复核、傅钧烨2026-09-08签收候选ba495b54e6939c2bb1c4a07592400f82c0292864，签收提交28bf474643cda6c59480ea3d478749269d5cf3eb。原范围是实现与合成验证，不是测量有效性或正式准入。本轮目录整理不继承原签名。

## 四阶段验收

| 阶段 | 动作 | 完成要求 |
|---|---|---|
| 1 真值 | 消费v2.2帧、冻结结构及独立实际来源 | AC1来源与版本一致；实际null不复制目标 |
| 2 题库 | 四层八题、结构完整步骤和未知选项 | AC2区别hold_1/hold_2、inhale_1/inhale_2和跨周期 |
| 3 材料 | 同事件双条件、无语义编号、公开与私有分离 | 新合成输出复算；题目/选项/键不按条件改变 |
| 4 交接 | 保留作答/缺失状态和材料身份 | AC3原签收绑定；真实片段、标注和有效性仍由下游完成 |

## 执行与归属

`py -3.14 agent/tasks/U12-02/execution/build_evidence.py --check`复算当前合成输出，`py -3.14 agent/tasks/U12-02/execution/verify.py`核对本包及Q-02/E-02交接。TASK及inputs/execution/evidence/outputs/archive固定结构。运行模块measurement.py仍在共享技术模块，接口与行为不改；旧生成器、状态工具、技术记录、说明及原合成五文件实际归档。新输出不覆盖原件。

## 上下游

F-05给步骤/周期身份，F-02给四层构念；S-02给真实独立标签，U-02/U-07给真实片段，Q-01/Q-02给形成性与等值检查，U12-04/U12-11给分析分母和正式冻结，U12-09消费来源复算。理解题在PANAS后测之后，不给800秒体验增加参与者操作；理解失败不隐去有效PANAS结果。

## 国内学习资料

- [Datawhale统计学习方法解答](https://datawhalechina.github.io/statistical-learning-method-solutions-manual/)：沿用原L-STAT学习统计复算；不以学习资料替代正式测量证据。
- [pytest中文文档](https://pytest.cn/en/stable/)：沿用原L-PYTEST测试步骤、缺失、双条件和篡改负例。
