# Agent执行层

人类阅读从[项目导航](../human/README.md)进入，新开发者从[开发上手](../human/developers/README.md)进入。

| 维护对象 | 权威入口 |
|---|---|
| 应用实现与合同 | [模块目录](modules/README.md) |
| 运行与未完成链 | [运行入口](runtime/README.md) |
| 当前设计 | [设计地基](design/design-foundation-20261008/README.md) |
| 状态与领取 | [治理入口](governance/README.md) · [任务导航](../human/tasks/README.md) |
| 验证证据 | [验证入口](validation/README.md) |
| 文件归属 | [目录规范](../human/project/repository-layout.md) |

当前任务设计权威为[固定引导与原生自适应基线](design/design-foundation-20261008/task-baseline.json)，逐包范围见[71包迁移记录](work/2026-10-08_新基线任务包迁移.md)。任务正文、当前交接、inputs/sources.json、outputs/design-revision.json、summary.json及人类LaTeX/PDF同步消费新要求。

统一目录仍为TASK.md、inputs、execution、outputs、evidence、archive；T-01已有design设备预览材料保留。旧TASK、总结与被替代交接原文位于各包archive/pre-design-baseline-20261008；旧软件测试和签收保持原范围，不证明新增适应已实现。

当前计划从注册表current_*列生成，原status及签收范围不因更新变化。READY包刷新输入；领取中原input_snapshot_id与候选身份保持，新要求以design_updates及input_impacts显式交接。正式运行消费已获准合同和研究协议，设计包不能授权采集。

人类证据以summary.tex和summary.pdf维护，不新增DOCX。生成工具为tools/build_task_reviews.py，专项一致性检查为tools/verify_task_design_baseline.py；独立分发生成器仍位于治理目录，默认发布校验要求来源已在Git索引，--local只检查本地内容。根目录结构迁移的历史记录见[root-migration.md](root-migration.md)，与新业务完成分别计数。
