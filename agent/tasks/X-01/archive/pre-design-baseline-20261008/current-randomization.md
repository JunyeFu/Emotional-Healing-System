# X-01当前随机化实现与交接

## 已签收范围

傅钧烨2026-09-06审阅f59c182候选及已有机器/独立Agent结果签收PASS，记录cad3e90；没有表述为本人重跑。六轮历史Agent最终PASS，其自身未能运行pytest，动态33项和根564项由原主工作区提供。当前DONE只覆盖原软件/合成范围，本轮工具迁移与复现改动未新签署。

## 实际清单和概率

generate_list仅支持stage_1/stage_3，固定48完整块，各分层每块两臂各24。阶段一每臂24天气排列恰好一次；阶段三balanced_random覆盖24排列，frozen_policy记录weather_sequence=null由X-03后续供策略。阶段域隔离同种子的派生，公开种子承诺不是公开原种子；实际种子保管及分层切点仍待正式冻结。

任务通用“可变块”没有变成任意块长实现，当前仍固定48；旧合成192条只是两层各两块，不是最终招募N或正式清单。平衡按分配计数，COMPLETE/INCOMPLETE/ABORTED只用于审计，不定向补完成格。

完整均衡顺序的位置概率为1/4、1/3、1/2、1，配合清单哈希/索引追踪。random_draw是已选动作区间中点见证，不是在线RNG采样记录；state_snapshot_hash来自会话/阶段/位置/候选/动作身份，不是生理状态哈希。policy_decisions用于均衡清单的动作记录，不能传随便的策略顺序就宣称获得真实行为概率。X-03冻结策略必须记录真实候选分布和实时状态，不能借该帮助函数冒充。

## 揭示、存储和正式门

custodian导入，allocator分配揭示，auditor记录结果/平衡/链检查；角色是调用方参数检查，不是Windows身份认证或已落实人员分离。SQLite BEGIN IMMEDIATE完成原子分配；同请求须阶段/层/版本/预约一致，跨请求同预约、错版、清单耗尽、篡改或越权失败关闭。状态、清单、审计引用必须一致。

eligibility/device_readiness/dedup_reservation三项均通过，CurrentGateEvidenceVerifier在新揭示前调用真实门验证器；SnapshotGateEvidenceVerifier仅开发，无正式能力。formal_capable是装配声明与验证器标记共同形成的软件回执，不自动证明真实资格、专机ACL或机构授权。G-05需落实实际存储、角色、保管、权限与活动。

P-01的X01AssignmentGate核对已揭示清单、索引、层、块、臂、版本、预约/许可及固定序列；不自己推进体验或登记暴露。G-02 adapter从预约允许回执生成证据，真实当前状态验证仍由装配提供。前测、揭示、教学及暴露次序消费U12-06/U12-11与P-01，不能把设备检查完成等于整个实验准入。

## 阶段三和Level C缺口

阶段三独立清单不等于可运行frozen_policy会话；动态步骤决策及P-01v2.2实时接口由X-03对齐，保留真实概率与策略支持。核心论文不依赖阶段三。Level C传入生成器会STAGE_UNSUPPORTED，Q-03需独立适配，不能把stage_1标签换成level_c。

正式分层、正式清单、角色人员、专机权限、实际资格验证、真实运行及X-03仍缺；现有测试中AlwaysTrue验证器和临时SQLite只是合成测试，不是这些条件已满足。

## 当前执行与原件整理

verify_x01.py与generate_evidence.py实际移入Agent，原路径无转发副本。原README按字节归档，原模块导航当前说明；测试导入新路径，Schema/业务/原六份证据及签署不改。

从仓库根运行 `py -3.14 agent/tasks/X-01/execution/verify.py`。只复核原报告运行 `py -3.14 agent/tasks/X-01/execution/verify_x01.py`。另存复现：

```powershell
py -3.14 agent/tasks/X-01/execution/generate_evidence.py --output-root <不存在的新目录>
```

目录已存在即拒绝，逐文件排他创建，不覆盖原件；内容仍为SYNTHETIC_ONLY。脚本不提供正式清单生成功能；实际正式清单用业务write_plan排他创建，并经真实冻结与存储资格审查。原件完整性验证读唯一权威Schema，不把外部输出副本当新Schema权威。
