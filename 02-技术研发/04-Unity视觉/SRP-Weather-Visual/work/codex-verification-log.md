# U-01 验证记录（第三轮审查）

> 日期：2026-09-07 | 分支：codex/u-01-reliable-control | HEAD：cd3b7cc
> 审查人：Grip 第3轮 | 验证人：Hermes Agent

---

## 一、测试环境

| 项目 | 值 |
|------|-----|
| Unity 版本 | 6000.4.9f1 |
| 操作系统 | Windows 11 |
| .NET 运行时 | Mono（Unity Editor 内置） |
| 测试框架 | NUnit 3 + Unity Test Framework |
| Python 服务器 | srp_session_core（本地 loopback mock） |

---

## 二、测试结果总览

| 测试套件 | 用例数 | 通过 | 失败 | 跳过 | 状态 |
|----------|--------|------|------|------|------|
| SRP.U01.EditModeTests | 82 | 82 | 0 | 0 | ✅ 全绿 |
| SRP.U01.PlayModeTests | 6 | 6 | 0 | 0 | ✅ 全绿 |
| **合计** | **88** | **88** | **0** | **0** | **✅** |

---

## 三、EditMode 用例清单（82 项）

### JsonLinesSerializationTests（14 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 1 | SerializeString_ProducesQuotedValue | JSON 字符串序列化 |
| 2 | SerializeInt_ProducesNumericLiteral | JSON 整数序列化 |
| 3 | SerializeBool_ProducesTrueOrFalse | JSON 布尔序列化 |
| 4 | SerializeNull_ProducesNullLiteral | JSON null 序列化 |
| 5 | SerializeNestedDictionary_ProducesNestedJson | 嵌套字典序列化 |
| 6 | SerializeArray_ProducesJsonArray | JSON 数组序列化 |
| 7 | SerializeSpecialCharacters_EscapesCorrectly | 特殊字符转义 |
| 8 | RoundTrip_SimpleDictionary | 简单字典序列化/反序列化往返 |
| 9 | RoundTrip_NestedStructures | 嵌套结构序列化/反序列化往返 |
| 10 | Decode_InvalidJson_ThrowsFormatError | 无效 JSON 抛 FormatException |
| 11 | Serialize_ControlEvent_VisibleStructure | control_event JSON 结构 |
| 12 | Encode_AppendsNewline | Encode 追加换行符 |
| 13 | Serialize_Float_PreservesPrecision | 浮点精度保持 |
| 14 | Serialize_Long_PreservesValue | long 类型值保持 |

### SessionMirrorTests（7 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 15 | InitialSnapshot_IsEmpty | 初始快照为空 |
| 16 | ApplySessionManifest_UpdatesSnapshot | manifest 应用更新快照 |
| 17 | ApplyControlEvent_UpdatesActiveSeq | control_event 更新 active_seq |
| 18 | ApplyControlEvent_ModuleEvent_UpdatesModuleId | module 事件更新 module_id |
| 19 | ApplyControlEvent_SegmentEvent_UpdatesSegment | segment 事件更新 segment |
| 20 | ResetState_ClearsAllFields | ResetState 清空所有字段 |
| 21 | ApplyControlEvent_NullThrows | null 参数抛 ArgumentNullException |

### AckManagerTests（13 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 22 | FirstEvent_IsAppliedFalse_AfterMarkApplied_IsAppliedTrue | 首次事件幂等判定 |
| 23 | CreateAck_AfterMarkApplied_ReturnsApplied | MarkApplied 后 ACK result=applied |
| 24 | DuplicateEvent_IsAppliedTrue_CreateAckReturnsDuplicateIgnored | 重复事件 duplicate_ignored |
| 25 | DuplicateEvent_MultipleEvents_DetectedIndependently | 多事件独立去重 |
| 26 | CreateAck_HasCorrectFields | ACK 字段完整性 |
| 27 | CreateAck_Rejected_HasErrorCode | rejected ACK 携带 error_code |
| 28 | CreateAck_Applied_HasNullErrorCode | applied ACK error_code=null |
| 29 | CreateAck_AllResultTypes | 所有 AckResult 类型覆盖 |
| 30 | AppliedEventIds_PersistAcrossReconnect | 重连后已应用事件持久化 |
| 31 | AppliedEventIds_NotClearedOnNewSession | 新会话不清除已应用事件 |
| 32 | Reset_ClearsAllApplied | Reset 清空所有已应用记录 |
| 33 | AppliedCount_IncrementsCorrectly | AppliedCount 正确递增 |
| 34 | OnEventApplied_EventFires | OnEventApplied 事件触发 |

### RenderReceiptManagerTests（12 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 35 | RegisterEvent_CreatesPendingReceipt | RegisterEvent 创建待处理回执 |
| 36 | CompleteRendered_CreatesReceiptWithCorrectFields | CompleteRendered 字段正确 |
| 37 | CompleteSkipped_HasSkippedResult | skipped 回执 |
| 38 | CompleteFailed_HasFailedResult | failed 回执 |
| 39 | GetUnsentReceipts_ReturnsCompletedUnsent | GetUnsentReceipts 返回未发送 |
| 40 | GetUnsentReceipts_ExcludesAlreadySent | GetUnsentReceipts 排除已发送 |
| 41 | CompleteRendered_ForUnregisteredEvent_CreatesAdHoc | 未注册事件 ad-hoc 路径 |
| 42 | DiscardAll_ClearsAllState | DiscardAll 清空所有状态 |
| 43 | OnReceiptReady_EventFires | OnReceiptReady 事件触发 |
| 44 | ReceiptId_IsUnique | receipt_id 唯一性 |
| 45 | FrameSeq_Increments | frame_seq 递增 |
| 46 | RegisterEvent_NullThrows | null 参数抛异常 |

### ReconnectHandlerTests（10 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 47 | NewHandler_HasGenerationZero | 新 Handler generation=0 |
| 48 | SignalConnected_IncrementsGeneration | 连接成功递增 generation |
| 49 | SignalConnected_ResetsBackoff | 连接成功重置退避 |
| 50 | SetFaultMode_FailNextConnect_ShouldInjectFault | 故障注入 FailNextConnect |
| 51 | ClearFault_StopsInjection | 清除故障停止注入 |
| 52 | SetFaultMode_DropEveryNth_InjectsPeriodically | 周期性丢帧故障注入 |
| 53 | SetFaultMode_CorruptMessage_ShouldCorruptPeriodically | 周期性消息损坏故障注入 |
| 54 | ResetState_ClearsAll | ResetState 清空所有状态 |
| 55 | Abort_StopsReconnecting | Abort 停止重连 |
| 56 | OnGenerationChanged_FiresOnConnect | generation 变更事件触发 |

### UDP5006GateValidationTests（9 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 57 | Validate_ValidTelemetryFrame_ReturnsAccepted | 有效遥测帧 accepted |
| 58 | Validate_InvalidJson_ReturnsInvalidJson | 无效 JSON 拒绝 |
| 59 | Validate_MissingMessageType_ReturnsMissingMessageType | 缺少 message_type 拒绝 |
| 60 | Validate_WrongMessageType_ReturnsNotTelemetryFrame | 错误 message_type 拒绝 |
| 61 | Validate_WrongSchemaVersion_ReturnsSchemaViolation | 错误 schema_version 拒绝 |
| 62 | Validate_MissingRequiredField_ReturnsSchemaViolation | 缺少 required 字段拒绝 |
| 63 | Validate_EmptyBody_ReturnsInvalidJson | 空消息体拒绝 |
| 64 | Validate_FullTelemetryFrame_AcceptsAllFields | 完整遥测帧接受 |
| 65 | GateReceiptTracksStats | GateReceipt 统计跟踪 |

### ContractMessageStructureTests（6 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 66 | AckMessage_AllRequiredFieldsSerialized | ACK 消息 required 字段序列化 |
| 67 | RenderReceipt_AllRequiredFieldsSerialized | 渲染回执 required 字段序列化 |
| 68 | TransportHello_AllFieldsPresent | 传输 hello 字段完整性 |
| 69 | TransportWelcome_AcceptedTrue | welcome accepted=true |
| 70 | TransportError_ContainsCode | error 帧携带 error_code |
| 71 | SessionManifest_WeatherSequence_RemainsUnique | weather_sequence 去重 |

### ReliableControlClient_ErrorHandlingTests（11 项）
| # | 用例名 | 覆盖 |
|---|--------|------|
| 72 | CONNECTION_MISMATCH_TriggersSocketCloseAndReconnect | CONNECTION_MISMATCH → 重连 |
| 73 | NOT_PENDING_LogOnlyNoReconnect | NOT_PENDING → 仅日志 |
| 74 | REJECTED_LogOnlyNoAction | REJECTED → 仅日志 |
| 75 | TIMEOUT_LogOnlyNoAction | TIMEOUT → 仅日志 |
| 76 | UnknownErrorCode_IncrementsCounter | 未知错误码计数递增 |
| 77 | UnknownErrorCode_DegradesAtThreshold | 未知错误码阈值降级 |
| 78 | KnownErrorCode_ResetsCounter | 已知错误码重置计数器 |
| 79 | CONNECTION_MISMATCH_DoesNotIncrementCounter | CONNECTION_MISMATCH 不递增计数 |
| 80 | JsonParseFailure_IncrementsCounter | JSON 解析失败计数递增 |
| 81 | JsonParseFailure_DegradesAtThreshold | JSON 解析失败阈值降级 |
| 82 | ValidFrame_ResetJsonCounter | 有效帧重置 JSON 计数器 |

---

## 四、PlayMode 用例清单（6 项）

| # | 验收标准 | 用例名 | 覆盖 |
|---|----------|--------|------|
| 1 | AC1 | DuplicateEventId_SecondAckIsDuplicateIgnored | 重复 event_id → 第二次 ACK 为 duplicate_ignored |
| 2 | AC1 | StaleFramesRejected_DuplicateFramesDetected | 乱序/重复遥测帧检测 |
| 3 | AC2 | NoControlEvent_SessionMirrorUnchanged | 无控制事件 → 状态不变 |
| 4 | AC3 | V21HandshakeRejected_StopReconnect | v2.1 握手被拒 → 停止重连 |
| 5 | AC3 | Reconnect_IncrementsGeneration_SameClientId | 断连重连 → generation+1, 同 client_instance_id |
| 6 | AC3 | RenderReceiptFailure_HasCorrectFields | 渲染回执失败路径字段正确 |

---

## 五、手动验证项

| # | 验证项 | 结果 | 备注 |
|---|--------|------|------|
| 1 | 三个 DLL 编译零错误 | ✅ | SRP.U01.Runtime.dll、SRP.U01.EditModeTests.dll、SRP.U01.PlayModeTests.dll |
| 2 | .gitignore 覆盖 *.sln *.slnx *.csproj | ✅ | |
| 3 | U01_TASK_PLAN.md 已移出 Assets | ✅ | 在 work/ 目录 |
| 4 | U01.meta 存在 | ✅ | |
| 5 | git status 仅含任务相关文件 | ✅ | 无无关文件 |
| 6 | Git HEAD: cd3b7cc | ✅ | 分支 codex/u-01-reliable-control |

---

## 六、三审新发现（R3-1 ~ R3-6）

| 编号 | 严重级 | 问题 | 处置 | 状态 |
|------|--------|------|------|------|
| R3-1 | P0 | dev 模式自动确认钩子缺失 → 回执链路零证据 | 待修复 | ⏳ |
| R3-2 | P0 | PlayMode fixture 遥测帧违反 schema oneOf | 待修复 | ⏳ |
| R3-3 | P1 | 回执注册范围过宽，与服务器验收规则不对齐 | 待修复 | ⏳ |
| R3-4 | P2 | 回执 frame_seq 本地自增（建议改用 control_seq） | 记入 blackboard | ⏳ |
| R3-5 | P2 | received_monotonic_ns 在主线程取 | 记入 blackboard | ⏳ |
| R3-6 | P2 | 反射 helper 残留（ForceCloseTcpClient） | 建议顺手删除 | ⏳ |

---

## 七、附件

- 编译日志：见 `u01_round3_check.txt`、`u01_round3_check_b.txt`
- 代码审查基线：runtime-contract-v2.2.schema.json
- 服务器实现：srp_session_core/transport.py、core.py
