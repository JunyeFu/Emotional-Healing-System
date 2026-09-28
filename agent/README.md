# Agent 执行层

本层保存任务执行材料、结构化总结、验证结果和生成工具。人类入口位于 `../human/`。

统一结构：`tasks/<任务编号>/TASK.md`、`inputs/sources.json`、`execution/verify.ps1`、`evidence/verification.json`、`outputs/summary.json`、`archive/README.md`。共享生成工具在 `tools/`。

每包按读取权威输入、整理执行目录、复测与修复、生成 Word、审阅串联关系的顺序推进。任务注册状态和规范化状态分别记录；规范化不能代替任务签收。

当前迁移首包是 F-01。旧工程和共享治理文件尚在原目录，最终根目录收拢将在全部包的归属与路径依赖完成迁移后执行；当前新增两个目录不代表根目录迁移已完成。

命名固定：每包只有一个当前 `summary.json` 和一个人类 `summary.docx`。过期执行输出移入 `archive/`，写明原路径、替代文件和保留理由；没有理由的临时输出在确认无需使用后清理。已签署证据保留历史内容。
