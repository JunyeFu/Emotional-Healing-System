# U-01 第 5 轮指导单（终审·亲跑实测打回）

## 0. 本轮怎么回事

黄彬在 Unity Test Runner 亲跑 **EditMode → Run All**：85 个用例中 **3 红**（SRP.U01 的 82 个里挂 3 个；F03 的 3 个全绿）。PlayMode 尚未跑。

你上报的"89 测试全绿"与实测不符。**修复后禁止再用"全绿"两个字代替结果**，必须贴 Test Runner 实际数字。数字口径：**EditMode 82 + PlayMode 8 = U01 共 90 个用例**（另有 F03 的 3 个 EditMode 用例）。

三个失败均已定位到行，根因裁决如下。

---

## R5-1（P0·生产代码缺陷）：AckManager 三个事件是死事件

- **失败用例**：`AckManagerTests.OnEventApplied_EventFires`（U01EditModeTests.cs L630-639）
- **现象**：订阅 `OnEventApplied` 后调 `MarkApplied("evt-001")`，回调永不触发，`appliedId` 始终为 null。
- **根因**：`AckManager.cs` L40 / L43 / L46 声明了 `OnEventApplied` / `OnDuplicateIgnored` / `OnEventRejected` 三个事件，但**全代码库没有任何 Invoke 点**：
  - `MarkApplied`（AckManager.cs L75-81）只把 id 加进 `_appliedEventIds`，不触发事件；
  - `ReliableControlClient` L854-877 的 applied / duplicate 分支也不触发事件。
  - 事件声明了从不触发 = 死代码。
- **修法（改生产代码，不是改测试）**：
  1. `MarkApplied`：利用 `HashSet.Add` 返回值，**仅当新增成功时**在锁外 `OnEventApplied?.Invoke(eventId)`；
  2. 新增 `public void MarkDuplicate(string eventId)` → 触发 `OnDuplicateIgnored?.Invoke(eventId)`；client L860 重复分支（`IsApplied==true`）调用它；
  3. 新增 `public void MarkRejected(string eventId, string reason)` → 触发 `OnEventRejected?.Invoke(eventId, reason)`；在 client 发送 `result="rejected"` ACK 的位置调用。**若该发送点当前不存在，不要编造调用点**——在事件声明处注释"保留给未来 reject 路径"即可；
  4. 所有事件 Invoke 一律用 null 条件运算符 `?.`，空订阅安全；
  5. 注意锁内不 Invoke（避免回调重入死锁），先在锁内取 bool 标记、锁外触发。
- 现有测试 `OnEventApplied_EventFires` 不用改，修完即过。建议顺手补一个 `OnDuplicateIgnored` 触发用例（可选，P2）。

## R5-2（P0·测试代码缺陷）：CONNECTION_MISMATCH 用例反射注入类型不匹配

- **失败用例**：`R25_ErrorFrameClassification_Tests.CONNECTION_MISMATCH_TriggersSocketCloseAndReconnect`（U01EditModeTests.cs L1411-1426）
- **现象**：用例在 Arrange 阶段直接 **Error**（不是断言失败）：L1415 `new System.IO.MemoryStream()` 经反射 SetValue 到 `_stream` 字段，但 `ReliableControlClient.cs` L99 声明的是 `private NetworkStream _stream;`——MemoryStream 与 NetworkStream 无继承关系，反射抛 ArgumentException。
- **生产逻辑已核实无误**：`ClassifyRuntimeError`（client L726-734）对 `CONTROL_ACK_CONNECTION_MISMATCH` 正确执行 `OnTransportError` + `CloseSocketForReconnect`（L787-791：`_stream?.Close()` + `_tcpClient?.Close()`）。
- **修法（测试，二选一）**：
  - **方案 B（推荐，名实相符）**：client L99 字段类型 `NetworkStream` 放宽为 `System.IO.Stream`（L452 `_tcpClient.GetStream()` 返回 NetworkStream 是 Stream 子类、L553/561/580-581 用法均为 Stream 成员、L272/278/789 Close/null 均兼容，**已核实无连锁**）；测试保留 MemoryStream 注入，用例末尾加反射断言：注入的 stream 已被 Close（`!((System.IO.Stream)field.GetValue(_client)).CanWrite`，MemoryStream Close 后 CanWrite=false），证明关 socket 动作确实发生；
  - **方案 A（兜底）**：若 B 出现任何编译连锁，直接删测试 L1414-1418 四行注入（`_stream` 为 null 时 `CloseSocketForReconnect` 的 null 条件运算符本就安全），现有两条断言保持不变。

## R5-3（P1·测试期望过时）：FrameSeq_Increments 还在断言本地自增

- **失败用例**：`RenderReceiptManagerTests.FrameSeq_Increments`（U01EditModeTests.cs L796-806）
- **根因**：R3-4 已把 frame_seq 改为 `evt.control_seq`（RenderReceiptManager.cs L102，对齐 `generate_golden_trace.py` 的 frame_seq=control_seq 惯例，**生产改法正确，不要回退**）；但本用例两次 `RegisterEvent(CreateTestEvent(...))` 所用事件的 control_seq 相同（helper 默认 seq 固定），导致 r1.frame_seq == r2.frame_seq，`Is.GreaterThan` 断言失败。老逻辑本地自增时它能过，是因为测试在测一个已被合同废除的语义。
- **修法（测试）**：
  1. 两个事件显式给不同 control_seq（evt-001→1、evt-002→2；按 `TestHelpers.CreateTestEvent` 签名传 seq，或构造后赋值 `control_seq`）；
  2. 断言改精确语义：`Assert.That(r1.frame_seq, Is.EqualTo(1))`、`Assert.That(r2.frame_seq, Is.EqualTo(2))`——frame_seq 必须等于各自 control_seq；
  3. grep 全部 RRM 测试中的 frame_seq 断言，凡依赖"本地自增"语义的一律对齐 control_seq；ad-hoc 路径（未注册事件 CompleteRendered，RRM L231 附近本地计数器）的既有覆盖保持原样。

---

## verification-log 收尾项（上一轮 7 条继续有效）

修完代码后一并改 `work/codex-verification-log.md`：

1. L2 HEAD 改为**本次最新 commit hash**（不是 06965f7，也不是 160c1a7）；
2. 结果表 PlayMode 7→**8**、合计 89→**90**（EditMode 82 + PlayMode 8）；
3. 删掉 L23-24 行首多余的 `||`（表格错位）；
4. PlayMode 用例清单拆两行：dev_replay 正向自动确认 + formal_stage_1 反向不确认；
5. 第六节"三审新发现"R3-1~R3-6 状态全部从"待修复 ⏳"改"已修复 ✅"；
6. 手动验证表第 6 项 HEAD 更新为最新 hash；
7. 手动验证表补一行："EditMode 82 + PlayMode 8 全量亲跑全绿（黄彬 Test Runner 实测）✅"——**前提是真的全绿，没跑不许写**。

## 收尾要求

1. 一个 commit 包含 R5-1 / R5-2 / R5-3 全部修复 + verification-log 更新，commit message 写明三项；
2. 修完在 Unity 里**亲自 Run All：EditMode（82）和 PlayMode（8）两个 tab 都跑**，回报每个 tab 的 passed/failed 数字；
3. git status 只留任务相关文件；`*.csproj` / `*.sln` 不提交；Assets 下文件夹 meta 必须进 git；
4. 自审贴行号：R5-1 三个事件的 Invoke 点行号、R5-2 字段声明与新断言行号、R5-3 control_seq 赋值与新断言行号；
5. **不要 push**，等终审放行。
