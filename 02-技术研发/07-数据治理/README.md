# G-02 数据治理

> 当前结论：`DONE_WITH_EXTERNAL_GATES_TRANSFERRED`。G-02治理实现已签收；正式专机环境、机构期限、资产许可清零与实地消费已转交G-05，仍保持失败关闭。

本模块实现L0至L5分级、跨Level B/Level C/阶段一/阶段三的单次参与约束、隔离研究编号映射、审计与备份恢复，以及Unity资产许可门。它不承担真实设备读取、会话编排、随机分配、交互状态估计或统计解释。

## 实现入口

| 能力 | 权威入口 |
|---|---|
| 数据分级与最小权限 | [config/data_classification_v1.json](config/data_classification_v1.json)、[config/access_matrix_v1.json](config/access_matrix_v1.json) |
| 手机号规范化与HMAC | [srp_governance/phone.py](srp_governance/phone.py) |
| 跨阶段事务去重与审计链 | [srp_governance/registry.py](srp_governance/registry.py) |
| 隔离研究编号映射 | [srp_governance/identity.py](srp_governance/identity.py) |
| Windows凭据 | [srp_governance/credentials.py](srp_governance/credentials.py) |
| 备份恢复 | [srp_governance/backup.py](srp_governance/backup.py) |
| Manifest隐私门 | [srp_governance/privacy.py](srp_governance/privacy.py) |
| 正式环境检查 | [srp_governance/environment.py](srp_governance/environment.py)、[docs/formal_machine_setup.md](docs/formal_machine_setup.md) |
| Unity资产许可门 | [srp_governance/assets.py](srp_governance/assets.py)、[Unity Governance](../04-Unity视觉/SRP-Weather-Visual/Governance) |
| 下游消费规则 | [docs/downstream_contracts.md](docs/downstream_contracts.md) |
| 命令行 | [g02.py](g02.py) |
| 当前任务核验与Word | [Agent执行入口](../../agent/tasks/G-02/execution/verify.ps1)、[人类总结](../../human/tasks/G-02/summary.docx) |

固定HMAC凭据只允许首次初始化：目标已存在时`provision`失败关闭，密钥轮换必须另走显式审计流程。Manifest隐私门同时搜索独立值和普通文本中嵌入的手机号、邮箱，错误不回显原值。

## 公开Python接口

```python
from srp_governance import (
    audit_cross_stage,
    check_and_reserve,
    configure_formal_runtime,
    mark_exposed,
    normalize_phone,
    privacy_lint_manifest,
    release_before_exposure,
)
```

`check_and_reserve`的结果只包含`allowed`、`reason_code`、`reservation_id`、`audit_event_id`和`token_version`。返回值、异常和审计报告均不得包含原始手机号、规范化号码或HMAC令牌。

正式运行的`actor_id`固定使用不透明角色码`data-admin`，Windows账户只用于凭据和ACL鉴权，不写入去重库。暴露前释放原因必须是已登记的大写原因码，不接受自由文本。

## 三类隔离存储

正式运行必须把以下三者物理隔离：

1. `dedup/dedup_registry.sqlite`只保存HMAC令牌、阶段、状态和审计事件；
2. `identity/research_id_mapping.sqlite`只保存不透明招募引用到随机研究编号的映射；
3. `SRP/G02/dedup-hmac/v1`凭据只存在于专机Windows Credential Manager，密钥不进入仓库、SQLite、日志或普通备份。备份清单使用该密钥做域分隔HMAC认证，且备份包拒绝任何SQLite侧文件或额外文件。

保留期限保持`PENDING_INSTITUTIONAL_APPROVAL`。只有真实授权方给出可追溯编号后，才能设置`SRP_RETENTION_APPROVAL=APPROVED:<authority-id>`。

## 验证命令

```powershell
Set-Location 'D:\Agent\srp'
py -3.14 'agent/tasks/G-02/execution/verify.py'
```

该入口运行专项、合成演练、隐私、正式环境和资产门，新输出固定到`agent/tasks/G-02/evidence/runtime/`。
正式环境和资产门退出`2`表示正确阻断，汇总必须保留实际结果，不等于准入通过。原evidence为历史证据，不由新入口覆盖。
仓库隐私工具已迁入Agent层；仅扫描Git跟踪文件，新增候选文件应暂存后再执行发布前检查。

## 当前门状态

| 门 | 当前证据 | 结论 |
|---|---|---|
| 合成跨阶段矩阵 | 32个主动/既往暴露组合、释放重入、完成/退出阻断、并发和密钥认证备份恢复均通过 | 合成技术路径通过 |
| 正式专机 | 治理根、备份根、密封恢复证据、数据管理员账户、凭据和保留期限均未配置 | 正式录入阻断 |
| Unity资产 | 2026-09-28本轮复扫233项、259条阻断；原189/215保留为2026-09-04历史结果 | 正式发布阻断 |
| 第二人复核 | 傅钧烨已完成候选级复核并在提交`ea132c8`签署`PASS` | 第二人复核门已关闭；G-02为`DONE`，外部门由G-05继续阻断 |

当前证据见[本轮核验](../../agent/tasks/G-02/evidence/verification.json)，历史证据见[evidence/](evidence)和[G-02_技术验收记录.md](G-02_技术验收记录.md)。本轮专项139项通过，含新增Agent证据目录负测试；历史签收138项不改写。
