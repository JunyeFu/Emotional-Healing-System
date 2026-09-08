# U12-07 涉及文件

> `inputs/`是领取时输入快照，只用于离线阅读和核对。不要在快照中实现；应修改下列项目权威路径。

## 输入文件

| 项目权威路径 | 包内快照 | SHA-256 |
|---|---|---|
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控/protocol_authority_v1.2.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控/protocol_authority_v1.2.json) | [inputs/01_protocol_authority_v1.2.json](inputs/01_protocol_authority_v1.2.json) | `3E5015BBA65588FF852E05B1831CB062E606F3ECB78C1F5B008FE61840D59DE6` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/u12_upgrade/consumers.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/u12_upgrade/consumers.json) | [inputs/02_consumers.json](inputs/02_consumers.json) | `2F68C3877531DB831C6CC4FDF22A0D039FA2491E988C4EFA8AA46A91C164A91E` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/u12_upgrade/study_manifest_v1.2.template.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/u12_upgrade/study_manifest_v1.2.template.json) | [inputs/03_study_manifest_v1.2.template.json](inputs/03_study_manifest_v1.2.template.json) | `43A720E65F10EB49818B3130143C57B7BF1DA106A312B9A9430603EC35DD088B` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/audit_upgrade/release_routes_v1.2.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/audit_upgrade/release_routes_v1.2.json) | [inputs/04_release_routes_v1.2.json](inputs/04_release_routes_v1.2.json) | `D9248B5EBE79EA40EB41A5CAD44DB0BF84BFB0A0EDAD085F8EC3192F37568331` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/audit_upgrade/task_milestones_v1.2.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/audit_upgrade/task_milestones_v1.2.json) | [inputs/05_task_milestones_v1.2.json](inputs/05_task_milestones_v1.2.json) | `D38328914584CDBBFA32601C89F3E50DD7A4D3A336930EBCD5A471CC7115BBA8` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-07/inputs/task_input.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-07/inputs/task_input.json) | [inputs/06_task_input.json](inputs/06_task_input.json) | `302E8C641B6DD877852B9AD4F8E5A97990DA4640F5C73D3D737C90FB0089A2AE` |

## 实现工作目录

- [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0)

## 权威规则

- 开始前读取项目根目录`AGENTS.md`并运行`git status --short`。
- 输入文件变化后重新生成任务包；哈希不一致的旧包不得继续分发。
- 文本快照统一为LF并移除行尾空白；二进制快照保持原始字节。
- 快照保留原文内容，其内部相对链接可能仍指向原目录；需要追踪链接时从上表打开项目权威文件。
- 大型工程、缓存、构建结果和个人配置不复制进任务包。
