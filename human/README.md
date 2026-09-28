# 人类审阅层

跨项目逐包总结使用[通用中文Word模板](templates/通用中文逐包任务总结模板.docx)，填写与Agent层回填规则见[模板说明](../agent/templates/task-review/README.md)。

从 [项目串联审阅](project-review.docx) 阅读总体偏离和交接关系，再打开各包 Word。Word 由 `agent/tasks/<编号>/outputs/summary.json` 生成，修订从执行层开始，再重新生成 Word。

| 顺序 | 任务包 | 人类总结 | 当前规范化结果 |
|---|---|---|---|
| 1 | F-01 合同与协议 | [总结](tasks/F-01/summary.docx) | 已补齐执行层与本轮复测，Word已完成页面审阅 |
| 2 | F-02 构念与测量 | [总结](tasks/F-02/summary.docx) | 当前适用入口已与v1.2对齐；模型候选审查与真实签收分开 |
| 3 | F-03 Unity工程基线 | [总结](tasks/F-03/summary.docx) | 执行工具已迁入Agent层，完整Unity复测通过；正式资产门仍阻断 |
| 4 | F-04 TD只读操作台 | [总结](tasks/F-04/summary.docx) | 执行脚本与新旧制品隔离；主机38项回归及历史制品身份通过，当前未重跑TD |
| 5 | F-05 步骤合同与迁移 | [总结](tasks/F-05/summary.docx) | 执行工具迁入Agent层，287项回归及新旧证据封存通过；当前指南与真实签收对齐 |
| 6 | G-01 研究治理材料 | [总结](tasks/G-01/summary.docx) | 当前稿与v1.2对齐，历史签署保留；外部资格、实际人员和现场产能仍待落实 |
| 7 | G-02 数据治理实现 | [总结](tasks/G-02/summary.docx) | 隐私工具迁入Agent层，139项专项和233项消费者通过；正式配置与资产门仍阻断 |
| 8 | P-01 会话编排 | [总结](tasks/P-01/summary.docx) | golden工具迁入Agent层，434项回归及800秒轨迹比较通过；核心前教学暴露接入仍待冻结 |
| 9 | P-02 追加记录与重放 | [总结](tasks/P-02/summary.docx) | 两个工具迁入Agent层，467项回归及6项golden复测通过，800秒合成负载通过；真实原件读取不由束清单授权 |

未进入本表的任务仍在规范化队列中；它们已有的 DONE、IN_PROGRESS 和 IN_REVIEW 状态以原任务注册表为准。
