# A-03 涉及文件

> `inputs/`是领取时输入快照，只用于离线阅读和核对。不要在快照中实现；应修改下列项目权威路径。

## 输入文件

| 项目权威路径 | 包内快照 | SHA-256 |
|---|---|---|
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控/protocol_authority_v1.1.json](D:/Agent/srp/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控/protocol_authority_v1.1.json) | [inputs/01_protocol_authority_v1.1.json](inputs/01_protocol_authority_v1.1.json) | `66DCF22A6B98E9B35FE069AA19373228E9E2070A2508F253801ACA3669E51794` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/03_步骤02_构念比较条件与测量/01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md](D:/Agent/srp/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/03_步骤02_构念比较条件与测量/01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md) | [inputs/02_01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md](inputs/02_01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md) | `BCA2CBF8DD2AB7E942D4C2C671D95860D5ED363E8353B977482925D88F1762C8` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/03_步骤02_构念比较条件与测量/02_F-02_验收记录.md](D:/Agent/srp/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/03_步骤02_构念比较条件与测量/02_F-02_验收记录.md) | [inputs/03_02_F-02_验收记录.md](inputs/03_02_F-02_验收记录.md) | `90E1C97EA29A3A1C367FD97B596786CDEFA7C915E338D1C153F15DE504F2D607` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/22_离线处理与科研分析/00_离线处理总设计.md](D:/Agent/srp/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/22_离线处理与科研分析/00_离线处理总设计.md) | [inputs/04_00_离线处理总设计.md](inputs/04_00_离线处理总设计.md) | `6B9D203D56D5B665FFFCB9638E3D4544B6BA3DC71935B52F690574DD5AA9688D` |
| [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/audit_upgrade/task_milestones_v1.0.json](D:/Agent/srp/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理/audit_upgrade/task_milestones_v1.0.json) | [inputs/05_task_milestones_v1.0.json](inputs/05_task_milestones_v1.0.json) | `285173B311500DB71B94CF6BD6A901154EF5A0BE57253671748EF593EA0171F3` |
| [02-技术研发/02-信号处理/评分模型设计.md](D:/Agent/srp/02-技术研发/02-信号处理/评分模型设计.md) | [inputs/06_评分模型设计.md](inputs/06_评分模型设计.md) | `C5789AE28253CE0C1D4D8C57AAB63D215C9517D1145A49DC72669784F456972D` |

## 实现工作目录

- [00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/22_离线处理与科研分析](D:/Agent/srp/00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/22_离线处理与科研分析)
- [02-技术研发/02-信号处理](D:/Agent/srp/02-技术研发/02-信号处理)

## 权威规则

- 开始前读取项目根目录`AGENTS.md`并运行`git status --short`。
- 输入文件变化后重新生成任务包；哈希不一致的旧包不得继续分发。
- 文本快照统一为LF并移除行尾空白；二进制快照保持原始字节。
- 快照保留原文内容，其内部相对链接可能仍指向原目录；需要追踪链接时从上表打开项目权威文件。
- 大型工程、缓存、构建结果和个人配置不复制进任务包。

## 新设计变更补充（原领取输入保持）

- [agent/design/design-foundation-20261008/task-baseline.json](design_updates/01_task-baseline.json)；DBCD6D126948011AD106C695E38DC4657E09E0395AF9EECAC4497220366623C3
- [agent/design/design-foundation-20261008/00-reasoning.md](design_updates/02_00-reasoning.md)；D7E979215E1329527AE704F46E3F7A9D2C26BB8AF1DDA8886C0554428412C8C6
- [agent/design/design-foundation-20261008/01-design.tex](design_updates/03_01-design.tex)；C142AB0F43D172D4054DB0FFB95A446196AD2DAFAC1A45AFA9687C1DC9176FBA
- [agent/design/design-foundation-20261008/01-design.pdf](design_updates/04_01-design.pdf)；5A62ABE98872F283BA2EC47EAD324BD87B65012EC9BBE39B12772144E87F6A33
- [agent/design/design-foundation-20261008/02-science.tex](design_updates/05_02-science.tex)；03AD1A02FE781406C6D15CCAC639D5A7F2497F320314507F0955DE5656B64F46
- [agent/design/design-foundation-20261008/02-science.pdf](design_updates/06_02-science.pdf)；E422C0F56D5898FC1C7D16CE9D13A49B5A60672C6C7FA89DD82B9E8F09B3FD0D
- [agent/design/design-foundation-20261008/03-decisions.tex](design_updates/07_03-decisions.tex)；9083235196072DABED8334EA21BCC22D206081DF786D58F796A1BCABBDE84CA8
- [agent/design/design-foundation-20261008/03-decisions.pdf](design_updates/08_03-decisions.pdf)；4E86834D042C590A38C6F794F65C2D6A68ADFDAF849FEF2E6402D983256CD3C3
- [agent/design/design-foundation-20261008/04-review-audit.tex](design_updates/09_04-review-audit.tex)；1D47E11D4C6DAB4D77B420F144DCAF272BC7F8017DB2AD51625B7754DCA8A519
- [agent/design/design-foundation-20261008/04-review-audit.pdf](design_updates/10_04-review-audit.pdf)；FD407713BD16B37B5323FE94BAAEAE4BE0FD10D040800B45E134C26180977573
- [agent/tasks/A-03/outputs/design-revision.json](design_updates/11_design-revision.json)；8FBBD6AA3EB2EF00BAC95DE73A5235B684EB02AD71C3656F8DA0CC434FC68C9A
- [agent/tasks/A-03/TASK.md](design_updates/12_TASK.md)；25916CD2C48EAAE073E18087A20250AE6DC2BF336F27FAC181F759F2A551B7E0
- [agent/design/design-foundation-20261008/05-control-spec.tex](design_updates/13_05-control-spec.tex)；5974115723E72901374370EF2BFD1FFF16D330500A2E315D5549774014021BF1
- [agent/design/design-foundation-20261008/05-control-spec.pdf](design_updates/14_05-control-spec.pdf)；14C9DAAD0D2C17B7CEA0EEF282533719BC43D3AF95F0A102B440F20F3C417D05
- [agent/design/design-foundation-20261008/06-paired-storyboards.tex](design_updates/15_06-paired-storyboards.tex)；8C6B1D0787D01813CC6FD1D2A636265C9D2F057D5D7F6B81BA37B29D9E2ECB70
- [agent/design/design-foundation-20261008/06-paired-storyboards.pdf](design_updates/16_06-paired-storyboards.pdf)；88E4C007642EFBEBDDD80FEEF3109A6DDC40CE874D62577510E80B1A8E046EB4
- [agent/design/design-foundation-20261008/07-protocol-candidate.tex](design_updates/17_07-protocol-candidate.tex)；94A840BC078B862F409C65CB4C674C5133E69E4699F436BF568E47F79D28A441
- [agent/design/design-foundation-20261008/07-protocol-candidate.pdf](design_updates/18_07-protocol-candidate.pdf)；69219843B56BF4B9950B07ACE502F31D96B3D51D6F0F55E57952C16F4CCBDE1F
- [agent/design/design-foundation-20261008/operational-design.json](design_updates/19_operational-design.json)；81738308099D660D614C25914C27458F4FC0E82CA1F158DAE7DA635FBD28EB9D
