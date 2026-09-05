# SRP审计升级工作区

本目录记录2026-09-05外部审计输入的接收、项目内复核、条件路线和治理接口。原始压缩包以只读来源制品归档于`external_source/`；来源记录保存原路径、归档路径、字节数、SHA-256、固定提交和清单验证结果。

## 当前裁定

- 批次0和批次1进入实施；UP-01至UP-12继续作为原任务子交付。
- A-06是第59项任务，也是唯一新增顶层任务。
- 阶段一主论文可独立收尾；阶段二和阶段三只有在统计支持、资源和外部准入通过后进入。
- N05与根目录项目规则冲突，明确不采纳。
- 批次2至4尚未因本目录存在而完成。

## 文件

- `source_record_v1.0.json`：外部输入身份和接收校验。
- `findings_disposition_v1.0.csv`：24项问题的本地分类与关闭责任。
- `upgrade_subdeliveries_v1.0.csv`：UP-01至UP-12与原任务、状态、证据和关闭门的绑定。
- `upgrade_evidence_manifest_v1.0.json`：12项子交付证据引用的确定性字节哈希；由`build_upgrade_evidence_manifest.py`生成。
- `release_routes_v1.0.json`：两条论文收尾路线和条件依赖。
- `a06_route_closure_v1.schema.json`：A-06真实范围回执、阶段三活动事实和结果族的关闭格式；未关闭前不存在实例文件。
- `task_milestones_v1.0.json`：A-03提前规格、真实接入和盲态校准里程碑。
- `external_capability_matrix_v1.0.csv`：G-05按活动拆分的资格需求。
- `evidence_record_v1.schema.json`：任务签收和资格证据最小字段。

验证入口为同级目录上方的`15_validate_audit_upgrade.py`。

G-05只有在13项能力均为`QUALIFIED`、每个`evidence_ref`均指向可验证的`external_capability`记录且其引用内容身份可重算时才能转为DONE。A-06关闭时须设置仓库外绝对目录`SRP_A06_EVIDENCE_ROOT`；目录内三类固定JSONL台账必须与关闭记录中的相对路径、字节哈希和记录数一致。A-06签署报告必须位于仓库内，并同时包含完整Git候选身份和复核人。没有这些条件时验证器失败关闭。
