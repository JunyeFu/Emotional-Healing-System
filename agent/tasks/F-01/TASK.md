# F-01 合同与协议执行包

原任务状态为 DONE，规范化责任人为本任务 Agent；历史实现人为 Codex，真实第二审核人为傅钧烨。

本包交付 v2.1 JSON Schema、Python校验器、合法非法fixture、兼容字段过滤、幂等控制账本、迁移说明与端口登记。验收逐项覆盖 AC1合法fixture、AC2失败关闭和重复控制、AC3兼容字段忽略。

按 `inputs/sources.json` 读取项目原路径，运行 `execution/verify.ps1`，结果写入 `evidence/verification.json`。修复事实与交接说明写入 `outputs/summary.json`，由 `agent/tools/build_task_reviews.py F-01` 生成 Word。

当前修复：合同入口关于 F-05 的状态已从候选待复核改为已签收；v2.1/v2.2仍分版本消费。历史报告保留原文。

下游使用者包括 G-02、P-01、F-05及Unity/TD消费者；SessionCore仍是唯一流程权威。本包不交付网络运行服务或真实设备采集。
