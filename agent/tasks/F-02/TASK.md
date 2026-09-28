# F-02【研究设计】构念与测量材料规范化

原注册任务为“Gate2构念SCCI四层理解与Level A/B材料”，状态保持 DONE。历史 DONE 只覆盖候选材料与模型 AC 审查，不推定真人活动已实施或真实第二人已经签署。

## 责任与范围

历史生产者：GPT Deep Research + Codex；历史审查：Codex独立AC审查（2026-08-06）。本轮执行：Codex，负责目录、当前使用入口、复测及Word总结。不代填历史缺失的真实第二人结论。

AC1：SCCI只作操纵检查；AC2：理解及心智努力保持条件中性，问卷目标不超过5分钟；AC3：项目筛选在查看条件效果前冻结，提供序数项目及条件差异审查方法。

## 执行顺序

1. 读取 inputs/sources.json 指向的历史材料及当前 v1.2、U12-02、U12-04 权威。
2. 以 execution/build_current_measurement.py 生成 outputs/current-measurement.md。历史联合门及粗相位题不再作为当前使用入口。
3. 执行 execution/verify.ps1，保存实际结果，不以静态检查代替测量有效性。
4. 从 outputs/summary.json 生成 human/tasks/F-02/summary.docx 与项目串联Word，逐页检查。

## 下游

Q-01消费专家材料；Q-02消费候选条目、两条件访谈和用时预算；U12-02提供v2.2步骤实例题；U12-04提供结果分析规格。正式采用须由对应任务负责人取得真实测量、许可和冻结证据。

共享实现保留在原模块目录，本包只引用，不复制源码。最终根目录迁移尚未完成。
