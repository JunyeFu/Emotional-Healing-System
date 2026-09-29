# 步骤实例测量运行模块

U12-02保持2026-09-08限定候选签收DONE。运行公开接口make_material和score_response仍在measurement.py，不改变行为、版本或八题结构。

当前任务与交接见[Agent任务](../../tasks/U12-02/TASK.md)和[当前说明](../../tasks/U12-02/outputs/current-measurement.md)。活动生成器已迁入Agent执行层：

```powershell
py -3.14 agent/tasks/U12-02/execution/build_evidence.py --check
py -3.14 agent/tasks/U12-02/execution/verify.py
```

[当前标注计划](../../tasks/U12-02/outputs/annotation-plan.md)仍仅规划；真实信号、片段、测量有效性和正式准入未完成。[旧说明与合成证据归档](../../tasks/U12-02/archive/README.md)保留原件。当前新输出不继承原签名。
