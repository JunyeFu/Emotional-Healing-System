# G-02 正式专机配置与检查

> 本流程只用于获批后的专机准备。配置人员必须是指定数据管理员；不得在聊天、提交、日志或截图中粘贴手机号、HMAC密钥或密封恢复内容。

## 1. 前置授权

开始前必须具备：

- 数据管理员Windows账户；
- 独立加密治理卷和独立加密备份位置；
- 密封恢复副本的存在性证据路径，内容本身不进入仓库；
- 保留期限授权编号；
- 第二人见证的账户与ACL检查安排。

任一项缺失时只允许运行合成演练。

## 2. 目录与环境变量

治理根与备份根不得位于Git仓库、Unity工程或普通用户同步目录。以下仅为当前PowerShell会话示例，实际盘符由专机配置记录决定：

```powershell
$env:SRP_GOVERNANCE_ROOT = '<encrypted-governance-root>'
$env:SRP_GOVERNANCE_BACKUP_ROOT = '<encrypted-backup-root>'
$env:SRP_SEALED_KEY_RECOVERY_EVIDENCE = '<sealed-copy-evidence-path>'
$env:SRP_DATA_ADMIN_ACCOUNT = '<windows-data-admin-account>'
$env:SRP_RETENTION_APPROVAL = 'APPROVED:<authority-id>'
```

`SRP_GOVERNANCE_ROOT`内固定生成：

```text
dedup/dedup_registry.sqlite
identity/research_id_mapping.sqlite
```

两库不得共享字段、外键或目录权限继承到无关账户。

Windows数据管理员账户只用于凭据与ACL鉴权。治理库中的操作者统一记为角色码`data-admin`，不落盘Windows账户名。

## 3. ACL与加密检查

1. 用BitLocker或等价的Windows卷加密能力确认治理根和备份根均受保护；
2. 去除普通用户、设计成员和分析账户的继承写权限；
3. 数据管理员具有治理库读写权限；
4. 项目负责人只获得汇总审计和获批数据层权限；
5. 第二人记录账户、根路径、检查时间和结论，但不记录任何密钥值。

检查器只返回布尔结果与原因码，不输出ACL明细中的个人信息。

## 4. 凭据创建

只有数据管理员在确认目标名后执行一次：

```powershell
py -3.14 'D:\Agent\03-SRP\02-技术研发\07-数据治理\g02.py' provision-credential `
  --confirm-target 'SRP/G02/dedup-hmac/v1'
```

命令生成32字节随机密钥并写入当前账户的Windows Credential Manager，不返回密钥。目标名或`SRP_DATA_ADMIN_ACCOUNT`不匹配时必须拒绝。

## 5. 正式环境门

```powershell
Set-Location 'D:\Agent\03-SRP'
py -3.14 '02-技术研发/07-数据治理/g02.py' check-environment `
  --repo-root . `
  --output '<controlled-evidence-path>/formal_environment_report.json'
```

只有输出`G02_FORMAL_ENV_PASS`且第二人确认报告来自目标专机，才允许调用`configure_formal_runtime(repo_root)`。任何检查失败都必须保持正式流程关闭。

## 6. 备份恢复演练

- 仅使用SQLite在线备份API；不得复制活动数据库文件；
- 恢复目标必须为空目录；
- 依次验证备份SHA-256、密钥认证清单、Schema版本、审计链尾、凭据可用性、恢复授权和合成决策；
- 备份包只允许`dedup_registry.sqlite`、`audit_anchor.json`和`backup_manifest.json`，拒绝`-wal`、`-shm`或其他侧文件；
- 密钥不进入数据库备份；
- 首次正式录入前和每次权限或存储变更后重新演练；
- 演练报告只含不透明ID、结果码、哈希和时间，不含联系方式。

## 7. 关闭条件

以下任一情况必须停止正式使用：

- 保留期限重新变为待确认；
- 治理根、备份根或密封恢复证据不可访问；
- 数据管理员账户或ACL发生未审查变化；
- 凭据缺失或长度不符；
- 审计链、备份哈希或恢复合成决策失败；
- 仓库隐私门发现受控文件或联系方式。
