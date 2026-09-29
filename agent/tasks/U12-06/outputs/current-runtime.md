# U12-06 当前正式入口与待完成接线

## 当前结论

U12-06由傅钧烨领取，IN_PROGRESS，分支codex/u12-06-formal-gate。历史领取时间未登记，不补造日期。本轮整理分支并非成员实施分支，不把目录规范化作为新实现提交或DONE。

consumers.json中的六个本包消费者仍PENDING_RUNTIME_MIGRATION；无本包实际接线验收、独立复核或第二人签署。旧内容核验记录READY/未领取已过期，其原字节归档；当前记录由作者Agent更新，不能继承旧记录标题中的独立身份。

## 三种版本与当前行为

研究protocol_authority_v1.2是研究范围与冻结合同；F-05运行Schema2.2携带步骤实例和呼吸配置；P-01传输配置仍1.1。不能用运行2.2检查或旧研究1.1分类器替代研究1.2准入，也不能改历史合同让版本数字看起来一致。

现有SessionCore默认开发依赖拒绝formal路径；正式manifest要求Schema2.2、呼吸配置版本/哈希、传输配置及分配一致。首start还要求prepare ACK、暴露回执。当前formal_readiness是可注入接口，现有测试以合成formal_capable适配器能到PREPARED，没有读取真实研究冻结或批准。这是测试边界与待接线事实，不是实机正式运行已发生或已有生产漏洞已被利用。

本包evidence/runtime-observations.json复用现有测试fixture记录上述行为；不连接设备、不发TCP/UDP、不写真实分配或暴露库。旧用例名称包含all_real_gates，但依赖实际是formal-fixture:PASS，不能按用例名解释为真实资格已通过。

## 六消费者实际职责

| 消费者 | 当前入口 | 待完成的研究v1.2检查 |
|---|---|---|
| session_prepare_start | srp_session_core/core.py | prepare和首展示前核对活动准入/冻结；教学可能早于核心start，不遗漏暴露起点 |
| formal_readiness_gate | srp_session_core/gates.py | 真实批准范围、锁定字段、构建/算法/配置及真实链身份；返回可审阅回执，不能只信formal_capable |
| tcp_prepare | srp_session_core/transport.py | 调用受保护核心及记录代理；检查失败不得发送prepare/start，不另建裸发送路径 |
| allocation_reveal | srp_randomization/store.py | 在当前资格/冻结核验后揭示，已有资格/设备/预约三门不自动等于新研究合同全部条件 |
| durable_recording | srp_session_store | 新研究准入与同一记录代理配合；manifest耐久写成功只证明存储，不证明研究放行 |
| unity_formal_build | FormalBuildGate.cs | 发布门与研究门分别核对，开发授权不当研究授权；通过场景和资产检查不证明审批/数值已锁定 |

TD控制尚由T-02实现；正式请求不能绕过Python研究权威。A-01/P-02离线重放不得重新揭示分配、发送控制或登记暴露。开发与合成fixture单列，不能生成LIVE_E2E或正式活动证据。

## 交付边界与负测试

研究manifest当前UNFILLED_TEMPLATE_NOT_APPROVAL且formal_collection_allowed=false；主要效应界、N、教学预算、量表许可、机构范围、保留、停止、缺失计划、构建、LIVE_E2E、运行接线证据和预注册仍未完成。0.075是候选护栏，不因非空就当冻结，800秒是默认核心长度而非整个活动时长。

后续实施以真实准备/批准范围及U12-11冻结输入为依据，缺字段、错范围、错版本、错构建、失效批准与缺真实链逐入口拒绝。正式Level C与阶段一冻结条件分别按活动合同，不以未开展阶段三的资格卡住已获准核心路线，也不借早期静态许可放行设备或正式研究。

对prepare、首展示/start和分配揭示分别证明拒绝发生在不可逆动作之前；暂停/重连不得绕过受保护路径。记录代理与核心使用同一实例，存储失败按P-02既有中止语义。接口失败不能用内存记录、模拟信号或分类器结果补成正式成功。

## 输入保留与收尾

当前领取包inputs、manifest、候选身份和input_snapshot_id全部保留。2026-09-08旧候选四文件移入archive/candidate；原task_input是领取包来源，精确迁移映射让验证器继续核对原字节，不更新冻结副本。当前上游修订另读当前交接，并由成员按影响记录处理，不能擅自覆盖旧输入。

P-01/F-05/G-02/P-02已签收范围保留，不将本包材料移位当这些底座失效或新接线已验收。研究冻结G-03、灰盒/真实链I-01、[U12-09当前一致性](../../U12-09/outputs/current-consistency.md)和U12-11数值各自交证据。本轮不改六项PENDING，不代填独立PASS或真人签名。
