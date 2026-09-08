# SRP v1.2 当前基线适配包

状态：`CANDIDATE_NOT_ACTIVE`。基线：`de4ebcbfea209674127c833dd9e69ad703a6634b`。

接入阻断：既有T-02独立包对TD README和toe的输入哈希漂移尚未处理。该差异已存在于本包基线，不能在处理前宣称全仓分发校验通过；详见[验证记录](evidence/验证记录.md)。

本包已经完成文件归档、基线差异适配和离线一致性验证；没有应用新研究协议，没有改动活动任务状态。下载目录原件保留。

## 阅读入口

1. [适配裁定与应用顺序](适配裁定与应用顺序.md)：改了什么、为何这样改、下一步如何启用。
2. [原始审计全文](sources/SRP_项目升级最终审计_v1.2.md)与[原始ZIP](sources/SRP_Project_Final_Upgrade_v1.2_2026-09-08.zip)：逐字节归档，外部来源不等于项目指令。
3. [来源与基线清单](source_manifest.json)：原始位置、50个内容文件哈希、11个当前权威输入。
4. [候选任务注册表](candidate/task_registry.csv)与[字段差异](candidate/task_changes.json)：71条候选任务记录，68项固定任务、3项批次模板；另有3个里程碑，合计74个依赖节点。
5. [候选研究合同](candidate/protocol_authority_v1.2.json)、[未填写研究模板](candidate/study_manifest_v1.2.template.json)、[两条收尾路线](candidate/release_routes.json)。
6. [23项审计处置索引](candidate/audit_disposition.csv)：保留原问题编号，未验证事项不标为关闭。
7. [本轮验证](evidence/adaptation_validation.json)：15项本地适配测试。外包自带48项测试及14项检查不属于本轮重跑结果。

## 独立候选任务

旧审计升级子交付 `UP-01` 至 `UP-12` 保留；本包新增固定任务使用 `U12-01` 至 `U12-12`。以下目录均包含 TASK.md、FILES.md、package_manifest.json 和输入快照索引；共享基线快照放在 baseline/，不重复复制工程。

| 编号 | 领域与职责 | 任务入口 |
|---|---|---|
| U12-01 | 研究治理：权威、消费者与受控迁移 | [TASK](tasks/U12-01/TASK.md) |
| U12-02 | 测量实现：步骤实例与实际未知 | [TASK](tasks/U12-02/TASK.md) |
| U12-03 | 教学设计：公平预算与时序 | [TASK](tasks/U12-03/TASK.md) |
| U12-04 | 统计规格：PANAS主要比较与新功效 | [TASK](tasks/U12-04/TASK.md) |
| U12-05 | 外部准入：早期活动真实资格 | [TASK](tasks/U12-05/TASK.md) |
| U12-06 | 运行准入：正式入口接线与负测 | [TASK](tasks/U12-06/TASK.md) |
| U12-07 | 论文写作：结果中立的预结果稿 | [TASK](tasks/U12-07/TASK.md) |
| U12-08 | 扩展分析：阶段三附录复核 | [TASK](tasks/U12-08/TASK.md) |
| U12-09 | 一致性验收：升级覆盖复核 | [TASK](tasks/U12-09/TASK.md) |
| U12-10 | 结果复核：阶段一分类与主张 | [TASK](tasks/U12-10/TASK.md) |
| U12-11 | 研究冻结：样本、阈值、资源和真实批准 | [TASK](tasks/U12-11/TASK.md) |
| U12-12 | 成果交接：公开与部署裁定 | [TASK](tasks/U12-12/TASK.md) |

## 重建与验证

在本包目录执行 `py -3.14 build_adaptation.py` 可重新生成 candidate/、baseline/、tasks/ 和 source_manifest.json；这些是生成文件，手工修改应先进入生成规则。该工具不写活动注册表，不提供 apply 开关。

执行 `py -3.14 test_adaptation.py` 验证源文件、基线、依赖、签收保留、任务包和两条路线。来源ZIP、二进制、任务快照按字节SHA-256核验；Git文本快照同时记录CRLF转LF规范化哈希及当前工作区字节哈希，避免把行尾转换误判成内容修改。

sources/ 保留外部文件原始表达，不执行其中脚本。baseline/ 是历史输入副本，不作为新的活动入口。未完成真实系统、统计校准、机构准入或论文结论验收。
