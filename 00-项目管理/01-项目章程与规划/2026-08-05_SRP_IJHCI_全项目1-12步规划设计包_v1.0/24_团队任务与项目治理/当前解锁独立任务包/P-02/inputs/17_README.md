# P-02 Session Store

> 状态：`TECHNICAL_IMPLEMENTATION_CANDIDATE`。本模块提供L0/L1不可覆盖追加、完整性校验和确定性重放；它不推进会话状态，也不表示设备链或完整系统联调已经完成。

## 职责

- `SessionArchive`：排他创建会话归档，追加L0/L1，生成检查点和最终封存；
- `DurableManifestStore`：实现P-01 `ManifestStore`接口，manifest耐久落盘后返回门回执；
- `RecordingSessionCore`：代理纯`SessionCore`，先提交操作和输出，再把控制交给运行主机；
- `RecordingTelemetryPublisher`：先写L1同步帧，再调用P-01 UDP发布器；
- `ReplayReader`：验证manifest、记录链、检查点、段文件和封存哈希；
- `SessionReplayer`：只重放完整提交的核心调用，不连接外部进程或重复执行外部门动作。

旧`05-通信协议/csv_logger.py`继续作为`LEGACY_DEV_ONLY`保留，不是P-02正式记录入口。

## 公共接口

```python
DurableManifestStore.append_manifest(manifest, config_hash) -> GateReceipt

SessionArchive.append_raw_packet(packet) -> AppendReceipt
SessionArchive.append_l1(record_type, payload, now_ns) -> AppendReceipt
SessionArchive.checkpoint(now_ns) -> CheckpointReceipt
SessionArchive.seal(summary, now_ns) -> SessionSeal

RecordingSessionCore.prepare/apply_operator_request/advance/
    confirm_delivery/transport_failure/finish/snapshot

ReplayReader.verify(mode="strict|recover") -> IntegrityReport
ReplayReader.iter_l0(source_id=None)
ReplayReader.iter_l1(record_type=None)
SessionReplayer.replay_core(core_factory=None) -> ReplayReport
```

`RecordingSessionCore`和P-01 `ControlServer`、`SessionRuntimeHost`使用同一个代理实例。代理内部仍调用纯`SessionCore`，所以流程、时钟、状态和控制序号权威没有迁移到存储层。普通调用遵循`operation_begin -> SessionCore调用 -> 组件记录 -> operation_commit`；`prepare`在P-01完成合同、语义、隐私和分配检查后，于存储门回调排他建档并耐久写入`operation_begin`，随后P-01才建立`PREPARED`状态和控制输出。

## 目录与耐久性

```text
<root>/sessions/<sha256-derived-session-key>/
  archive.json
  l0/segment-000001.jsonl
  l1/segment-000001.jsonl
  tails/l0.json
  tails/l1.json
  checkpoints/checkpoint-000001.json
  seal.json
  writer.lock
```

- 路径键由域分隔SHA-256派生，不直接使用`session_id`；
- manifest、检查点和封存文件采用排他创建；
- JSONL记录包含连续序号、前项哈希和当前记录哈希；
- 每次耐久同步原子更新独立尾锚；L1必须与尾锚完全一致，L0只允许最后一次同步后的批量尾部尚未锚定；
- `archive.json`对除`envelope_hash`外的完整归档头做域分隔哈希；未封存恢复也必须先在写锁内重新验证归档头、记录链和封存状态；
- L1每次提交执行`flush + fsync`；L0按100毫秒或64 KiB批量同步；
- 64 MiB自动换段，跨段保持同一序号和哈希链；
- 已封存会话拒绝任何追加；同一会话只允许一个写者；
- 中断恢复不截断旧段，只创建新段写入`PROCESS_INTERRUPTED`并封存，后续运行必须使用新`session_id`。

配置见[session_store_config_v1.json](config/session_store_config_v1.json)，机器格式见[contracts](contracts/)。

## L0与L1

L0按设备通知包保存原始字节、来源策略、包序号、设备时间、主机接收单调时间、时钟域和样本数。缺失包必须使用`payload=None`、`sample_count=0`和大写原因码，不得补零。

L1保存manifest上下文、核心调用与提交、控制、会话事件、策略决策、审计、ACK、渲染回执、同步/SQI帧、时钟同步、存储事件和最终摘要。L0/L1只接受`research_id`、`reservation_id`等不透明引用；G-02禁入字段只在错误中暴露原因码和JSON路径。

## 正式环境

开发使用显式临时目录：

```python
store = DurableManifestStore.development(root)
```

正式候选只能通过环境工厂创建：

```powershell
$env:SRP_SESSION_DATA_ROOT = 'D:\SRP-Data'
$env:SRP_SESSION_WRITER_ACCOUNT = $env:USERNAME
$env:SRP_SESSION_WRITER_ROLE = 'primary_operator'
```

```python
store = DurableManifestStore.from_formal_environment(repo_root)
```

工厂要求数据根位于仓库外、当前账号匹配，并通过G-02加密、ACL和角色能力检查。直接构造`DurableManifestStore`只能得到开发能力。

## 下游交接

- D-01/D-02调用`append_raw_packet`，每个设备维护自己的递增`packet_seq`，不需要了解文件布局；
- S-02/I-01通过`append_l1`或`RecordingTelemetryPublisher`提交同步帧和质量字段；
- A-01先调用`verify()`，再使用`iter_l0/iter_l1`重建后续层；
- `strict`要求完整封存；`recover`只用于识别并封存中断数据，不能恢复原体验进度。

## 验证

```powershell
Set-Location 'D:\Agent\03-SRP'
py -3.14 -m pytest '02-技术研发/tests/session_store' -q
py -3.14 '02-技术研发/srp_session_store/generate_golden_archive.py'
py -3.14 '02-技术研发/srp_session_store/generate_stress_report.py'
```

golden归档消费P-01四模块轨迹并验证19个控制、19个ACK、12个渲染回执、54个会话事件和46次核心调用。压力证据模拟800秒、32万PLUX样本、10.4万Polar样本和1.6万L1同步帧；在归档对象仍存活时按100秒采样，并同时冻结1 MiB暖机后增长上限和每100秒128 KiB趋势上限。
