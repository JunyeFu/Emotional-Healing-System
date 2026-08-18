# 呼吸事件与Protocol Fidelity离线设计 v1.1

## 事件与固定复合模块

识别吸气、呼气、停顿、补吸和不确定事件。风暴、炙烤、暴雪和褪色分别对应箱式、长呼气、等时和双吸长呼结构；只能解释四个天气—呼吸复合实例。

## 应有周期机会

每个模块从冻结目标时间线生成`expected_cycle_opportunity`，包含机会ID、模块、目标开始/结束、必需事件和容差版本。每个机会只能取一个状态：

```text
COMPLIANT
NONCOMPLIANT
TECH_UNOBSERVABLE
```

`TECH_UNOBSERVABLE`只由预注册技术原因触发，包括信号质量不足、时间同步失效、设备断流或冻结降级。判定不得查看提示条件和后续结果。

## 三个并列指标

```text
opportunity_completion_rate
  = (COMPLIANT + NONCOMPLIANT) / expected_cycle_opportunities

PF_observable
  = COMPLIANT / (COMPLIANT + NONCOMPLIANT)

PF_conservative
  = COMPLIANT / expected_cycle_opportunities
```

主要参与者级`protocol_fidelity_primary`由四个模块机会结果各占25%聚合。若技术不可观测使模块不可评估，主要结果标记缺失并进入参与者级预注册缺失处理；不得使用剩余模块重新平均。`PF_observable`与`PF_conservative`作为并列支持和敏感性结果。

## 周期符合判定

1. 通过模块特定结构硬门，包括阶段顺序和必需事件；
2. 通过模块特定阶段时长与总周期容差；
3. 可观测但不符合任一门的机会记为`NONCOMPLIANT`。

容差、最低机会数和覆盖门必须在Level C依据盲态数据冻结，不能根据正式条件差调整。

## Gate 1

```text
D = mean(PF_scene_native) - mean(PF_abstract_pacer)
Delta_NI = 0.075
H0: D <= -0.075
H1: D > -0.075
```

全部随机分配分析集和完整四模块分析集的双侧95%置信区间下界均严格大于`-0.075`才通过。`0.05`作更严格敏感性；`0.10`只作情景展示。

## 报告

- 应有机会、可观测机会和三类机会计数；
- 三个PF指标及模块差异；
- 阶段边界误差、结构错误和目标周期完成率；
- 技术不可观测原因、降级时长和条件差异；
- 人工标注F1、MAE、kappa和分歧处理。

正式至少10%会话由两名盲态标注员复核；Level C按冻结方案覆盖关键结构和质量区间。
