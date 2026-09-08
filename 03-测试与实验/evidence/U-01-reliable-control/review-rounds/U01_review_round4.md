# U-01 第四轮审查（终审）指导单

当前 HEAD：06965f7。三审 6 项修复复核结果：

| 项 | 结论 |
|---|---|
| R3-1 dev 钩子代码 | ✅ 实现正确（client L902-912：仅 segment 事件、仅 dev_mock/dev_replay、formal 不触发；SessionMirror.RuntimeMode 已暴露） |
| R3-2 fixture 步骤字段 | ✅ L436-439 已改活动组（target hold_1 / actual inhale_1，与 phase 一致） |
| R3-3 注册收窄 | ✅ L889 仅 segment，注释语义完整 |
| R3-4 frame_seq=control_seq | ✅ RRM L102 |
| R3-6 反射 helper 删除 | ✅ 已删，L894 用 DropClient()（InjectDependencies 的字段注入反射保留，合理） |
| R3-5 接收线程时间戳 | ⏸ P2 观察项，记 blackboard 下轮，不阻塞 |
| git/blackboard | ✅ status 干净，blackboard 有 R3 记录 |

## 终审不通过，差两项（都是收尾级，工作量很小）

### R4-1（必须）补 dev 钩子端到端测试用例

三审指导单 R3-1 明确要求的 e2e 用例**没有写**：PlayMode 仍是 6 个老用例，全文件无 dev_mock/dev_replay 引用。钩子代码目前零覆盖——88 全绿证明不了钩子生效。

在 U01PlayModeTests.cs 新增 1 个 [UnityTest]（参照现有用例的握手/mock 服务器骨架）：

1. manifest 用 **dev_replay**（或 dev_mock）模式（EditMode fixture L373/L1319 有 dev_mock manifest 写法可参考），走完正常握手；
2. 让 mock 服务器向 client 下发一个 **segment** 控制事件（module_id/segment 与 manifest 一致）；
3. `yield return new WaitForSeconds(...)` 等回执刷出（FlushPendingReceipts 在 Update 里，留足 1-2 秒）；
4. 断言（复用 mock 服务器已有统计，不许只跑不断言）：
   - `server.ReceiptIdCount >= 1`（回执真的产出并到达服务器）；
   - `server.DuplicateReceiptCount == 0`（R2-2 单发送路径不回归）；
   - 解析收到的 render_receipt 行：`result == "rendered"`、`event_id` == 所发 segment 事件 id、`frame_seq` == 该事件的 control_seq（R3-4 顺带验证）；
5. 反向断言：formal 模式（formal_stage_1）manifest 下同流程 **ReceiptIdCount == 0**，证明 formal 不自动确认（这条可以并进同用例或加一个用例，二选一，但必须有 formal 侧证据）。

### R4-2（必须）verification-log 更新

- HEAD 哈希 cd3b7cc → 更新为本次修复后的最新 hash；
- 测试结果表补入新用例（PlayMode 6 → 7，总数 88 → 89，以实际为准）；
- 新增一行手动/自动验证项："dev 模式 segment 回执端到端到达 mock 服务器、formal 模式不自动确认"。

## 放行条件

R4-1、R4-2 完成后：commit（先不 push），报新 hash + EditMode/PlayMode pass 数。我只做这两项的定点复核，过了立刻放行 push，然后走 TASK.md 回填 + 傅钧烨第二人复核。
