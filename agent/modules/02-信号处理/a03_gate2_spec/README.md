# A-03 SPEC 与当前执行入口

当前范围、执行和交接见 [Agent 任务包](../../../tasks/A-03/TASK.md) 与 [当前统计说明](../../../tasks/A-03/outputs/current-statistics.md)。历史 SPEC 的真人签署与报告不改写。

本模块目前提供合成计分、FDR、阶段错误汇总、旧有序联合门及确定性模拟。`score_panas(evaluation_mode="formal")` 始终拒绝，`evaluate_ordered_gate` 的正式模式始终返回不可评估；不是提供冻结回执后即可使用的正式实现。理解计分是旧八项 fixture，不替代 U12-02 步骤实例测量；序数模型仅有候选规格，没有真实数据模型拟合交付。

从仓库根执行本轮核验：

```powershell
py -3.14 agent/tasks/A-03/execution/verify.py
py -3.14 agent/tasks/A-03/execution/reproduce.py
```

复现工具在本包 `evidence/runtime/` 下创建新的运行目录，只比较历史输出，不覆盖原件。模拟 CLI 同样拒绝已有目标文件。24、85、96及三个 NO_GO 均是历史假设下的合成检查，不是当前 PANAS 主结果的功效或正式样本量。

旧 README 原文见 [历史归档](../../../tasks/A-03/archive/README_spec_legacy.md)。A-03 仍 IN_PROGRESS；SPEC 已签收，REAL/CAL 尚待完成。
