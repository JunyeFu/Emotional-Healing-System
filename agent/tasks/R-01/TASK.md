# R-01【体验设计】四层候选语法与完整表示方案

状态：注册表DONE，仅覆盖候选设计材料；本轮为双层规范化，不新增研究或真人验收。原生产者GPT Deep Research+Codex，原复核为Codex独立AC审查，不是团队人员签字。本轮执行Codex。

## 目标与验收

- AC1：目标、实际、累计、降级的输入、时间尺度、禁止耦合和失败行为可检查；Schema和正负fixture可重跑，真实双审单独记录。
- AC2：比较完整提示表示方案，不把效果归因于天气、几何或位置一个变量。
- AC3：六类视觉混杂定义可测；数值为工程候选，真实渲染及Level证据才支持正式冻结。

原工作量4人日。前置F-02；交付给V-01/V-03、S-02、U-07、Q-01/W-01和U12-03。实际领取及依赖仍以注册表为准。

## 过程

1. 对照原材料和v1.2，区分保留定义与已替代的研究指令。
2. 整理校验工具，执行Schema元校验、双条件与四类负例、相关回归。
3. 发布当前适用入口，明确U-02与后续天气实现的交接；从Agent总结生成本包及串联Word。

## 固定入口

- inputs/sources.json：实际权威与历史来源，不复制冻结输入。
- execution/verify.ps1：仓库根重跑；Python3.14、既有jsonschema/pytest。
- evidence/verification.json：本次实际检查，不承担真实视觉或研究结果。
- outputs/current-representation.md：当前消费者先读；历史Schema不是v2.2运行合同。
- outputs/summary.json → human/tasks/R-01/summary.docx：审阅由执行层回填。
- archive/README.md：历史保留和旧入口移除理由。

技能：交互表示设计、JSON Schema、公平性审查；国内资料见项目技能表L-RESEARCH/L-MARKDOWN。当前未指定新的真实签收人，由团队总监安排，不代填签署。
