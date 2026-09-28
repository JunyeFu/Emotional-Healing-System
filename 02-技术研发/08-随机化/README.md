# X-01随机化实现与当前交接

实现候选f59c182已由傅钧烨2026-09-06签收，注册DONE；范围为阶段一/三清单、SQLite分配与揭示、概率和完整性审计、P-01/G-02接口及合成验证。不是正式随机化清单或真实会话完成。

当前执行说明见[Agent交接](../../agent/tasks/X-01/outputs/current-randomization.md)；[签署原件](../../03-测试与实验/X-01_第二人审核报告_已签署.md)保持原文。共享srp_randomization、配置、Schema和合成原证据仍是本目录唯一实现。

从仓库根复核：`py -3.14 agent/tasks/X-01/execution/verify.py`。复现工具实际迁到Agent，运行generate_evidence.py时必须提供`--output-root <新目录>`，拒绝覆盖原报告；详细命令和新旧证据比较见当前交接。旧“仅建立入口”README已原文归档。
