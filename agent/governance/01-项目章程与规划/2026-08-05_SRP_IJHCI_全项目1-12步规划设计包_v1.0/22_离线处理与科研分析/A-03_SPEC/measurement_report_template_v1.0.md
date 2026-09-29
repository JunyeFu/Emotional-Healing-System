# Gate2测量报告模板 v1.0

## 1. 证据身份

- 数据束ID：`<RAW_EVIDENCE_BUNDLE_ID>`
- 分析配置ID：`<FROZEN_ANALYSIS_CONFIG_ID>`
- 量表与许可回执：`<INSTRUMENT_RECEIPT_ID>`
- 代码提交：`<COMMIT_SHA>`
- 分析集：`<FULL_ANALYSIS_SET / COMPLETE_FOUR_MODULE_SET / OTHER_PREDECLARED>`

缺少任一必需身份时，报告状态必须为`NOT_EVALUABLE`。

## 2. 工具适用性

| Level | 证据 | 结果 | 原因码 |
|---|---|---|---|
| A | `<CONTENT_REVIEW_REF>` | `<PASS/FAIL>` | `<CODE>` |
| B | `<COGNITIVE_INTERVIEW_REF>` | `<PASS/FAIL>` | `<CODE>` |
| C | `<BLIND_CALIBRATION_REF>` | `<PASS/FAIL>` | `<CODE>` |

## 3. 作答完整性

分别报告`RESPONDED`、`SKIPPED`、`TIMEOUT`和`TECH_UNPRESENTED`。技术未呈现不得并入错误数。按条件报告项目级缺失、参与者级缺失和原因码。

## 4. SCCI操纵检查

报告四个序数项目的分布、预设方向、累计logit模型、条件间项目功能差异与FDR结果。结论只允许说明表示差异是否被感知，不承担理解、努力或项目整体效果主张。

## 5. 四层理解

| 结果 | scene_native | abstract_pacer | 调整差与95%区间 | 冻结界限 | 判定 |
|---|---:|---:|---:|---:|---|
| 总分 | | | | | |
| 目标层 | | | | | |
| 实际层 | | | | | |
| 累计层 | | | | | |
| 降级层 | | | | | |

必须同时报告总分和预设关键层，不得用总分覆盖关键层失配。

## 6. 心智努力

报告1至9分分布、调整差与95%区间。方向为分数越低越省力；不得与SCCI或理解分数合成总分。

## 7. 阶段错误

按条件和天气模块报告错误数、可观测机会数、错误率及技术不可观测原因。主观结果不得补偿阶段错误保护门失败。

## 8. 有序联合门

依次填写工具适用性、SCCI方向、理解总分、关键层、心智努力和阶段错误。记录首个`FAIL`或`NOT_EVALUABLE`，后续项目只可描述，不得补偿或越级关闭Gate2。

## 9. 偏离与冻结

列出项目版本、计分规则、缺失规则、正式界限、分析集、模型和样本量的冻结回执。任何修改均须附时间、理由、查看条件效果的状态和影响评估。
