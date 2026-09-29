# Agent 执行层

本层保存任务执行材料、结构化总结、验证结果和生成工具。人类入口位于 `../human/`。

统一结构：`tasks/<任务编号>/TASK.md`、`inputs/sources.json`、`execution/verify.ps1`、`evidence/verification.json`、`outputs/summary.json`、`archive/README.md`。共享生成工具在 `tools/`。

每包按读取权威输入、整理执行目录、复测与修复、生成 Word、审阅串联关系的顺序推进。任务注册状态和规范化状态分别记录；规范化不能代替任务签收。

71项任务包已完成逐包整理；[根目录物理迁移](root-migration.md)正在推进，实际归属与进度见[root-layout.json](root-layout.json)。工作记录已迁入`work/`，旧工程和共享治理仍待迁移，整体目标未完成。

命名固定：每包只有一个当前 `summary.json` 和一个人类 `summary.docx`。过期执行输出移入 `archive/`，写明原路径、替代文件和保留理由；没有理由的临时输出在确认无需使用后清理。已签署证据保留历史内容。
