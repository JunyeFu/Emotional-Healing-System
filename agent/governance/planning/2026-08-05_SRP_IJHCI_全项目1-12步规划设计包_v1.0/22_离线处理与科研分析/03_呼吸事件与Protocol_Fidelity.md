# 当前呼吸事件与 PF 入口

当前事件交接见 [S-02](../../../../../agent/tasks/S-02/outputs/current-events.md)，离线消费见 [A-01](../../../../../agent/tasks/A-01/outputs/current-rebuild.md)。

`expected_cycle_opportunity` 三态为 `COMPLIANT`、`NONCOMPLIANT`、`TECH_UNOBSERVABLE`。技术不可观测不等于执行错误；应有机会、可观测机会和各类计数都要保留，不能事后删除分母。

PF 是功能护栏，不是主要情绪结果。非劣候选界值和信号容差尚需冻结，不能用旧 Gate 1 自动挡住 PANAS 结果报告。旧原文见 [历史 PF 设计](../../../../../agent/tasks/A-01/archive/03_呼吸事件与Protocol_Fidelity.md)，历史验证器已改读该原件。
