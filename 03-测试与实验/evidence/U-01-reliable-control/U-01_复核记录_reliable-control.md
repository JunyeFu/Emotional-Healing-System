# U-01 复核记录（reliable-control 实现）— 证据补录

> 实现分支：`codex/u-01-reliable-control`
> 代码 tip：`9be3b0c`（R7 修复：ReliableControlClient.Random 线程安全 + 测试修正，+71/-37）
> 文档回填：`d5be86b`（仅改 TASK.md 与 verification-log，代码与 9be3b0c 完全一致，`git diff 9be3b0c d5be86b --stat` = 2 files 全为文档）
> 本目录为 reliable-control 实现的证据补录，与 `03-测试与实验/evidence/U-01/`（unity-control 实现，main 已合入）相互独立，文件不重叠。

## 1. 测试结论与对应 commit

| 套件 | 结果 | 运行方式 | 对应代码与时间 |
|---|---|---|---|
| EditMode | 85/85 passed（含 F03 回归 3 项） | Unity 6000.4.9f1 Test Runner（Unity Hub GUI）Run All | 2026-09-07 实测（9be3b0c 期；d5be86b 代码一致，结论有效） |
| PlayMode | 9/9 passed，duration 16.66s | 同上，三轮实测 5/9 → 8/9 → 9/9 | XML 实证 start-time 2026-09-08T08:33:51Z（UTC） |

- **PlayMode XML 硬证据**：本目录 `playmode-results.xml`（原始字节复制自 `C:\Users\15744\AppData\LocalLow\DefaultCompany\SRP-Weather-Visual\TestResults.xml`，total=9 / passed=9 / failed=0 / skipped=0）。
- **EditMode XML 缺口说明**：Unity Test Runner GUI 结果文件为单文件固定位置，EditMode 运行结果被后续 PlayMode 运行覆盖，未能留档。EditMode 结论以 2026-09-07 实测记录（本目录 `codex-verification-log-excerpt.md` 与 review-rounds/ 全过程）为准。如第二人需要 EditMode XML 硬证据，在 Unity Hub 打开工程 → Window > General > Test Runner → EditMode Run All（预期 85 项全绿），结果文件归档后即可补齐。

## 2. PlayMode 三轮实测过程（详见 review-rounds/U01_review_round7.md）

| 轮次 | 结果 | 根因与处置 |
|---|---|---|
| 第一轮 16:04 | 5/9（195.66s） | 4 红三类根因：①生产 bug：ReliableControlClient.ReceiveLoop 后台线程调 UnityEngine.Random 致重连循环崩溃（→ 改 System.Random 实例字段）；②AC1_DuplicateEventId 断言期望值笔误（XML 实证幂等去重正常，前三条 ACK 断言全过）；③Formal 测试漏调 client.Connect()（第 8 处遗漏）+ while 死等无超时 |
| 第二轮 16:20 | 8/9 | AC3_Reconnect 断言时机早于重连握手完成，与 R2-3 语义（generation 在重连握手成功后递增）不符 |
| 第三轮 16:33 | **9/9（16.6s）** | 断言时机按实现语义修正后全绿；本轮结果即 playmode-results.xml |

生产代码仅 Random 线程安全一处修复，其余均为测试侧修正。

## 3. 七轮自审索引（review-rounds/ 目录）

| 轮次 | 文件 | 要点 |
|---|---|---|
| R1 | U01_review_round1.md | Grip 第 1 轮审查意见（P0-1~P0-6） |
| R2 | U01_review_round2.md | 交叉验证：ACK 幂等方向修正、UDP 死代码修复、fail-closed、组件接线 |
| R3 | U01_review_round3.md | R2 疑问复核 |
| R4 | U01_review_round4.md | 收敛轮 |
| R5 | U01_review_round5.md | 夜间收尾 |
| R6 | U01_review_round6.md | 清缓存重编译 + 修复验证（取证 HEAD e55b810） |
| R7 | U01_review_round7.md | 终轮收尾单：PlayMode 三轮裁决、verification-log 假报修正、静态遗留清单 |

另附：`playmode_result_0908.md`（夜修全程时间线：CLI 两次静默失败 → junction 污染 Safe Mode → 清 Library\Bee(149MB)+ScriptAssemblies(38.8MB) → Hub GUI 手动执行成功）、`codex-verification-log-excerpt.md`（verification-log U-01 entry 原文）。

## 4. 复现命令

```
Unity Hub 打开工程 D:\Agent\03-SRP\02-技术研发\04-Unity视觉\SRP-Weather-Visual
→ Window > General > Test Runner
→ EditMode 标签页 Run All（预期 85/85）
→ PlayMode 标签页 Run All（预期 9/9，约 17s）
```

- **已知工具链问题**：Unity CLI batchmode `-projectPath` 含中文路径传参编码 bug，两次静默失败实证（02:38 PID 33936、09:17 PID 95364，均零日志零产出）；junction 绕行会污染编译缓存触发 Safe Mode（106 个 ILPP pipe 错误）。**不建议 CLI 方式，统一 Hub GUI。**
- 代码基线：`git checkout 9be3b0c`（或 d5be86b，代码相同）后打开工程。

## 5. 已知静态遗留（round7 R7-4，不阻塞收尾）

1. ReconnectHandler.cs:269 Random 位于协程内（主线程驱动），线程安全，已审计不改。
2. ReliableControlClient.cs L26-30 过时注释段（round6 已标记）。
3. LoopbackTcpServer finally 竞态：极端情况可能双 close，建议后续加状态位/Interlocked 保护。
4. `Assets/_Recovery/0 (4).unity` + `.meta` 为 Unity 强杀崩溃恢复垃圾，未提交、待授权删除，绝不 push。

## 6. 与 unity-control 实现的关系

见同目录 `U-01_双实现对照分析_reliable-control.md`。
