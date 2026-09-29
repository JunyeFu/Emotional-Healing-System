# G-05 当前外部准入与活动交接

早期静态与回放的范围及真人准备见[U12-05当前交接](../../U12-05/outputs/current-admission.md)，活动资格继续登记既有矩阵。

## 当前事实与职责

G-05未领取，状态WAIT_DEP_EXTERNAL，依赖G-01/G-02。现有十三项资格全部PENDING_EXTERNAL、evidence_ref空；已有软件/材料签收不属于实际资格。机构路径、M-001、批准期限、实名角色培训、正式专机与两周实地结果均待真实证据。

原包把E-01列整体硬门已过期；当前静态/回放由U12-05限定批准内容。真实设备和正式采集不得借静态许可放行。阶段一与可选阶段三、实验使用/论文展示/再分发分别审查。现有治理要求G-05整体DONE时十三项均QUALIFIED；活动资格与全包完成不是同一状态。阶段三未开展时不能伪造两项资格或DONE，亦不得擅改当前全包关闭规则。

资格校验器要求可验证的external_capability记录、对应scope、外部回执审阅、真实复核人、跟踪证据及内容身份。当前代码只能核验结构/身份，不能辨认机构文件法律真实性；实际原件审核和批准范围仍由真人完成。不能把模拟PASS记录或一个APPROVED字符串当机构授权。

## 正式机器配置说明

只在获批机器由指定数据管理员执行以下准备：治理根、备份根、密封恢复存在性证据、管理员与ACL、去重凭据、保留期限，共六类。配置后检查会展开多个子项，不限定报告恰好六行，必须所有适用checks均通过。

治理/备份根为仓库外独立加密位置，备份与治理根不互为子目录；密封恢复证据只证明存在，不含恢复秘密。按G-02配置说明确认最小权限与卷加密，受限记录不进入Git/Unity或同步目录。操作者授权由真实责任人指定，治理库操作者仍只记录角色码。

从当前检出根执行，凭据创建仅为获批后人工步骤，本轮不会调用：

```powershell
$env:SRP_GOVERNANCE_ROOT = '<approved-encrypted-governance-root>'
$env:SRP_GOVERNANCE_BACKUP_ROOT = '<approved-encrypted-backup-root>'
$env:SRP_SEALED_KEY_RECOVERY_EVIDENCE = '<controlled-existence-evidence>'
$env:SRP_DATA_ADMIN_ACCOUNT = '<authorized-windows-account>'
$env:SRP_RETENTION_APPROVAL = 'APPROVED:<real-authority-reference>'
py -3.14 '02-技术研发/07-数据治理/g02.py' provision-credential --confirm-target 'SRP/G02/dedup-hmac/v1'
py -3.14 '02-技术研发/07-数据治理/g02.py' check-environment --repo-root . --output '<controlled-evidence-path>/formal_environment_report.json'
```

凭据目标固定，已有有效密钥不得重复创建/覆盖；轮换须独立授权。工具不输出密钥。保留批准编号必须来自机构回执，任务执行者不自行填写期限。本机只读报告不是专机结果；正式报告须绑定真实机器、时间、执行人及另一人见证。

正式开始前使用SQLite在线备份API演练，恢复到空目录，验证认证清单、Schema、审计尾锚和合成决策；不复制活动数据库或-wal/-shm，不把密钥打包。缺根、ACL/加密不确认、凭据/期限失败仍阻断，不借开发环境适配器绕过。

## 资产与现场

最新Z-01实扫225项、269阻断：未登记、忽略文件、移除、哈希变化和待替换。原手册“三个组”不能当当前发布结果。每个实际资产及用途取得权利或真实替换/排除再复扫，不仅重建清单让哈希相等；许可原件索引由G-05保管，扫描由G-02执行，候选构建由U-08/Z-01验收。

U8用真实漏斗、工位、占用、值班、故障与恢复回答产能；G-01历史528/112/55至70分钟都是情景，不是冻结N或现场结果。阶段一所需产能先依当前研究数值和预算计算，阶段三按另行批准范围开展；不使用跨阶段重复参与补样本。出现NO_GO时记录原因与行动，不能补造成功数据。

## 权威与交接

现有audit_upgrade/external_capability_matrix_v1.0.csv保持状态权威；U12-05承接早期批准，G-03/G-04承接阶段锁定，U12-11消费阶段一真实数值与资源，W-03审查公开条件。受限原件留仓库外，仓库仅批准的脱敏凭证/索引和复核；真实联系方式、密钥、研究映射不入包。

当前无实际负责人或签收，本轮只修过期入口并只读复测。全包关闭规则含未开展阶段三资格与核心路线之间的处置，需后续治理任务明确；不在本轮把PENDING改成QUALIFIED或改研究Gate。
