# P-01 Python Session Core

> 状态：`DONE_WITH_BOUNDED_SCOPE`。P-01已由傅钧烨完成真实第二人复核；该状态只覆盖本模块合同、编排和本机传输，不代表Unity、TouchDesigner、真实设备或`LIVE_E2E`已经完成。

F-05已签收，保持本页公共方法不变；`contract_adapter.validate_message()`按消息版本分派合同，Manifest会话版本驱动控制、握手和遥测版本。正式会话要求v2.2与已加载的呼吸配置hash一致；接口对齐见[运行合同F-05文档](../05-通信协议/contracts/F-05_v2.2接口对齐基线.md)。

## 职责

`SessionCore`是核心体验的唯一会话、模块、段、单调时间和控制序号权威。Unity只维护由控制事件驱动的渲染镜像，TouchDesigner只读遥测。旧`main.py`和UDP v1.2继续作为`LEGACY_DEV_ONLY`保留。

```python
prepare(manifest, assignment, now_ns) -> CoreUpdate
apply_operator_request(request, now_ns) -> CoreUpdate
advance(now_ns) -> CoreUpdate
confirm_delivery(ack_or_receipt, now_ns) -> CoreUpdate
finish(reason_code, now_ns) -> SessionSummary
snapshot() -> SessionSnapshot
```

状态为`CREATED -> PREPARED -> RUNNING <-> PAUSED -> COMPLETED | ABORTED`。每个模块严格经过`demo -> closed_loop -> lock_transition`，默认25/150/25秒，四模块默认总长800秒。

## 顺序和研究接口

- v2.1只实现`FixedSequenceProvider`，不生成随机化清单；
- 阶段一和阶段三均衡随机要求4条与manifest逐位置一致的`PolicyDecision`；
- 阶段三冻结策略返回`ADAPTIVE_SEQUENCE_REQUIRES_V2_2`；这个历史原因码不表示F-05步骤v2.2已经支持自适应顺序，仍等待X-03升级顺序接口；
- PANAS后测不得进入会话编排；阶段一顺序不读取体验中数据改变；
- manifest先通过F-01合同和P-01语义检查，再经过G-02隐私、X-01分配、P-02追加存储和正式环境门；
- 默认依赖只允许开发回放。正式模式缺少任一真实适配器时返回`FORMAL_GATE_UNAVAILABLE`。

### 核心前教学交接

研究v1.2候选时序把分条件教学置于PANAS前测之后、核心之前。当前`SessionCore`只编排核心体验：`prepare`不登记暴露，第一次`start`才调用暴露门，因此本模块本身不能保证教学后的退出阻断。不能在登记之前展示条件教学，也不能把本轮核心回归当成教学流程通过。

P-01与U12-11后续须按冻结时序接入“首次条件教学之前登记”，保留G-02预约与暴露状态；验证教学后退出、核心未启动、再次预约均阻断。U12-06的正式准入仍须消费真实冻结与资格，本轮不增加未冻结的教学操作或改变六个公共方法。当前缺口见[数据治理消费合同](../07-数据治理/docs/downstream_contracts.md)。

## 本机传输

- TCP `127.0.0.1:5010`：UTF-8 JSON Lines、v1.0握手、控制ACK和渲染回执；
- UDP `127.0.0.1:5005/5006`：遥测版本由活动会话决定，同一完整帧最多20Hz镜像给TD和Unity；正式会话要求v2.2；
- 控制默认500毫秒ACK超时、最多3次同ID同序号发送、2000毫秒重连宽限；
- 传输只接受已经实际发送且当前等待确认的控制ACK；渲染回执必须关联已确认的`segment`控制，并严格匹配模块和分段；
- 正式模式下`end`未确认时不会保留完成结论，交付超时、拒绝或断连会转为`ABORTED`并尽力发送中止控制；
- TD连接不允许提交状态修改；T-02完成前只保留角色入口；
- 首次发送`start`前先登记暴露；登记成功后即采用保守不可回退语义，后续链路失败不释放暴露状态；
- 正式控制耗尽时生成并尽力发送`abort`后断开Unity，开发控制耗尽时暂停；
- UDP的20Hz上限由本机发布单调时钟约束，不信任帧内时间戳；不得填补缺失值或发送与核心快照不一致的帧。

配置见[protocol_config_v1.1.json](config/protocol_config_v1.1.json)，会话事件Schema见[session-event-v1.schema.json](contracts/session-event-v1.schema.json)，跨模块候选轨迹见[golden trace](fixtures/golden/four-module-trace-v1.json)。

## 验证

```powershell
Set-Location 'D:\Agent\srp'
py -3.14 'agent/tasks/P-01/execution/verify.py'
```

生成器已迁入[Agent执行层](../../agent/tasks/P-01/execution/generate_golden_trace.py)，只写本轮`agent/tasks/P-01/evidence/runtime`，不覆盖上述历史golden。相同manifest、分配和时钟产生相同控制、会话事件和`trace_hash`。P-02已签收，其不可覆盖落盘与确定性重放仍在`../srp_session_store/`；该签收不代表正式运行装配或真实设备全链已完成。

本轮规范化入口见[任务工作单](../../agent/tasks/P-01/TASK.md)，历史技术验收记录和真实第二人签署保留原字节及当时状态；当前证据从Agent执行层读取。
