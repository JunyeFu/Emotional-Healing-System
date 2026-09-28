# 人类审阅层

跨项目逐包总结使用[通用中文Word模板](templates/通用中文逐包任务总结模板.docx)，填写与Agent层回填规则见[模板说明](../agent/templates/task-review/README.md)。

从 [项目串联审阅](project-review.docx) 阅读总体偏离和交接关系，再打开各包 Word。Word 由 `agent/tasks/<编号>/outputs/summary.json` 生成，修订从执行层开始，再重新生成 Word。

| 顺序 | 任务包 | 人类总结 | 当前规范化结果 |
|---|---|---|---|
| 1 | F-01 合同与协议 | [总结](tasks/F-01/summary.docx) | 已补齐执行层与本轮复测，Word已完成页面审阅 |

未进入本表的任务仍在规范化队列中；它们已有的 DONE、IN_PROGRESS 和 IN_REVIEW 状态以原任务注册表为准。
