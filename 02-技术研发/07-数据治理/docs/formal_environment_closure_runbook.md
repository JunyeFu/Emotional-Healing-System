# G-02 正式环境门逐项关闭操作手册

> **版本**：v1.0-candidate
> **状态**：`READY_FOR_EXECUTION`（仅在获批专机上由指定数据管理员执行）
> **依据**：`docs/formal_machine_setup.md`、`evidence/formal_environment_report.json`（`formal_ready=false`，6 项检查未过）
> **安全约束**：不得在聊天、提交、日志、截图或本手册实例中粘贴手机号、HMAC 密钥或密封恢复内容；证据输出一律写入仓库外受控路径。

当前 6 项未通过检查（来自 `formal_environment_report.json`）：

| # | 检查码 | 含义 | 责任角色 |
| :---: | :--- | :--- | :--- |
| 1 | `GOVERNANCE_ROOT_UNSET` | 加密治理根未设置 | R-008 数据管理员 |
| 2 | `BACKUP_ROOT_UNSET` | 加密备份根未设置 | R-008 数据管理员 |
| 3 | `SEALED_KEY_EVIDENCE_UNSET` | 密封恢复副本证据路径未设置 | R-008 + R-011 数据保护官 |
| 4 | `DATA_ADMIN_ACCOUNT_UNSET` | 数据管理员 Windows 账户未指定 | R-001 项目负责人 |
| 5 | `DEDUP_CREDENTIAL_AVAILABLE` | 去重 HMAC 凭据未创建 | R-008 数据管理员 |
| 6 | `RETENTION_APPROVAL_PENDING` | 保留期限未获机构批准 | R-001 + 机构 |

---

## 第 1 项：治理根（GOVERNANCE_ROOT_UNSET）

- **前置**：专机已准备独立加密卷（BitLocker 或等价），卷不位于 Git 仓库、Unity 工程或用户同步目录。
- **操作**：
  1. 在加密卷上创建治理根目录（如 `<encrypted-governance-root>`）；
  2. 按 `formal_machine_setup.md` 第 3 节去除普通用户、设计成员和分析账户的继承写权限，仅数据管理员读写；
  3. 当前 PowerShell 会话设置 `$env:SRP_GOVERNANCE_ROOT = '<encrypted-governance-root>'`（实际盘符记入专机配置记录，不进仓库）。
- **验收**：目录内可成功初始化 `dedup/` 与 `identity/` 子目录结构；重新运行第 7 节检查命令后该项 `passed=true`。

## 第 2 项：备份根（BACKUP_ROOT_UNSET）

- **前置**：独立加密备份位置（与治理根不同卷或不同物理介质）。
- **操作**：
  1. 创建备份根目录并套用与治理根同级 ACL；
  2. 设置 `$env:SRP_GOVERNANCE_BACKUP_ROOT = '<encrypted-backup-root>'`。
- **验收**：备份根可写；检查命令该项 `passed=true`。

## 第 3 项：密封恢复证据（SEALED_KEY_EVIDENCE_UNSET）

- **前置**：密封恢复副本已按机构流程制作并封存；**内容本身不进入仓库、不出现在任何命令输出中**。
- **操作**：
  1. 制作密封副本的**存在性证据**（封存记录、保管人签字、日期），存于受控路径；
  2. 设置 `$env:SRP_SEALED_KEY_RECOVERY_EVIDENCE = '<sealed-copy-evidence-path>'`。
- **验收**：证据路径可读且不含密钥内容；检查命令该项 `passed=true`。R-011 数据保护官复核封存流程合规性。

## 第 4 项：数据管理员账户（DATA_ADMIN_ACCOUNT_UNSET）

- **前置**：已创建专用 Windows 数据管理员账户（非个人日常账户）。
- **操作**：
  1. R-001 指定账户并记录授权起止（不记录口令）；
  2. 设置 `$env:SRP_DATA_ADMIN_ACCOUNT = '<windows-data-admin-account>'`；
  3. 第二人见证账户与 ACL 检查（`formal_machine_setup.md` 第 3 节），记录账户名、根路径、检查时间与结论，不记录密钥值。
- **验收**：该账户为唯一具有治理库读写权限的账户；检查命令该项 `passed=true`。

## 第 5 项：去重凭据（DEDUP_CREDENTIAL_AVAILABLE）

- **前置**：第 1、4 项已关闭；操作者为数据管理员本人。
- **操作**（每个目标只执行一次，目标名不匹配必须拒绝）：

  ```powershell
  py -3.14 'D:\Agent\03-SRP\02-技术研发\07-数据治理\g02.py' provision-credential `
    --confirm-target 'SRP/G02/dedup-hmac/v1'
  ```

  命令生成 32 字节随机密钥写入当前账户 Windows Credential Manager，**不返回密钥**。
- **验收**：检查命令该项 `passed=true`。已有合法密钥时不得重复 provision 覆盖（轮换必须走独立、显式、可审计流程）。

## 第 6 项：保留期限批准（RETENTION_APPROVAL_PENDING）

- **前置**：机构（学院/伦理或数据管理部门）批准数据保留期限。
- **操作**：
  1. R-001 取得批准文件与授权编号；
  2. 设置 `$env:SRP_RETENTION_APPROVAL = 'APPROVED:<authority-id>'`；
  3. 批准文号同步回填 G-01-02 §8 与 G-01-03 §5.2 的保存期限字段（治理提交，版本化）。
- **验收**：检查命令该项 `passed=true`。

---

## 7. 总体验收（6 项全部关闭后）

```powershell
Set-Location 'D:\Agent\03-SRP'
py -3.14 '02-技术研发/07-数据治理/g02.py' check-environment `
  --repo-root . `
  --output '<controlled-evidence-path>/formal_environment_report.json'
```

1. 输出必须为 `G02_FORMAL_ENV_PASS` 且 `formal_ready=true`；
2. 第二人确认报告来自目标专机（机器指纹、时间、执行人记录）；
3. 按 `formal_machine_setup.md` 第 6 节完成一次备份恢复演练（SQLite 在线备份 API、空目录恢复、哈希与审计链尾验证）；
4. 上述全部通过后，才允许调用 `configure_formal_runtime(repo_root)`；任何一项失败保持正式流程关闭；
5. 结果回填 G-02 任务记录与看板；仓库内只登记结果码、哈希与时间，不登记路径中的个人信息。

## 8. 关闭后持续约束

- `formal_machine_setup.md` 第 7 节停止条件全程适用（保留期限回退、根不可访问、ACL 未审查变化、凭据缺失、审计链/备份哈希失败、隐私门命中任一即停止正式使用）；
- 每次权限或存储变更后重新执行备份恢复演练与第 7 节检查；
- 本手册不涉及 Unity 资产门（3 个阻断组）与正式联系方式录入，它们独立于本门继续阻断。

---

## 版本记录

| 版本 | 日期 | 修改内容 | 负责人 |
| :--- | :--- | :--- | :--- |
| v1.0-candidate | 2026-08-21 | 初始建立：把 `formal_environment_report.json` 的 6 项失败检查映射为逐项操作、验收与责任角色，附总体验收与持续约束 | Codex（G-02 治理辅助） |
