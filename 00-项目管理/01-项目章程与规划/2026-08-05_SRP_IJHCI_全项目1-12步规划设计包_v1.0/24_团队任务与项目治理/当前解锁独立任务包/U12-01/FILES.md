# U12-01 涉及文件

> `inputs/`是领取时输入快照，只用于离线阅读和核对。不要在快照中实现；应修改下列项目权威路径。

## 输入文件

| 项目权威路径 | 包内快照 | SHA-256 |
|---|---|---|
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/protocol_authority_v1.2.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/protocol_authority_v1.2.json) | [inputs/01_protocol_authority_v1.2.json](inputs/01_protocol_authority_v1.2.json) | `9315DD8287EFB87EFA4EDE9ACBF7831FF79CE75DAB7ACC7F1E935F770907CD1F` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/task_registry.csv](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/task_registry.csv) | [inputs/02_task_registry.csv](inputs/02_task_registry.csv) | `FE006BACC30D0C8DC7A86F4551E34F058FB6E3D165D3A9E6598655219A5B9849` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/task_changes.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/task_changes.json) | [inputs/03_task_changes.json](inputs/03_task_changes.json) | `211594080528BAC1055785D95EEF52C50A0DFD94FC095EF7EA48737E2CEB0377` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/release_routes.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/release_routes.json) | [inputs/04_release_routes.json](inputs/04_release_routes.json) | `D9248B5EBE79EA40EB41A5CAD44DB0BF84BFB0A0EDAD085F8EC3192F37568331` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/task_milestones.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/candidate/task_milestones.json) | [inputs/05_task_milestones.json](inputs/05_task_milestones.json) | `623CAD652FBBD6A4B24275DEC6347E3314F5E4F9BC91763401A1B4351F084CB5` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/source_manifest.json](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/source_manifest.json) | [inputs/06_source_manifest.json](inputs/06_source_manifest.json) | `098AA9FB25F9C5AECA225C573DB36710D7FB9CEC9AEFC7286DEB65C4BA820546` |
| [00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/升级前收尾.md](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/升级前收尾.md) | [inputs/07_升级前收尾.md](inputs/07_升级前收尾.md) | `B3ED6D9D5CDBE4F9E83810D2453F3A44F3E6BE2B533C54FBD6D8E72736E32DD2` |

## 实现工作目录

- [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理)
- [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控](D:/Agent/03-SRP/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控)
- [Tools/Governance](D:/Agent/03-SRP/Tools/Governance)
- [04-成果与交付/PDF简报](D:/Agent/03-SRP/04-成果与交付/PDF简报)

## 权威规则

- 开始前读取项目根目录`AGENTS.md`并运行`git status --short`。
- 输入文件变化后重新生成任务包；哈希不一致的旧包不得继续分发。
- 文本快照统一为LF并移除行尾空白；二进制快照保持原始字节。
- 快照保留原文内容，其内部相对链接可能仍指向原目录；需要追踪链接时从上表打开项目权威文件。
- 大型工程、缓存、构建结果和个人配置不复制进任务包。
