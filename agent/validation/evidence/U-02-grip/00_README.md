# U-02 D3 证据索引

任务：U-02【Unity】四层 SceneAdapter 实现与降级
分支：codex/u-02-grip
采集：2026-09-20，Unity 6000.4.9f1 EditMode batchmode，OMEN (Windows)

| # | TASK 必需证据 | 文件 | 状态 |
|---|---|---|---|
| ① | 接口测试 | `01_editmode_results.xml`（+ `editmode_run4.log`） | 98/98 Passed，exitcode 0 |
| ② | 参数快照 | `02_parameter_snapshot.md` | 已对照 inputs/07，快照测试 8/8 |
| ③ | 层级隔离测试 | `03_layer_isolation_report.md` | 24 个隔离/封印用例全通过 |
| ④ | 降级录像 | `04_degradation_demo/V03_degradation_demo.mp4`（+ README/frames/player） | 五阶段 120 帧，已合成 MP4 |

## 接口测试总览（98）

| 套件 | 用例数 |
|---|---|
| V03BackgroundSealTests | 4 |
| V03DegradationPolicyTests | 8 |
| LayerIsolationTests | 8 |
| LayerZeroCrosstalkTests | 12 |
| ParameterBoundsSnapshotTests | 8 |
| V03QualityBehaviorMatrixTests | 9 |
| V03RecoveryLockTests | 7 |
| V03FrameGoldenTests | 6 |
| V03FrameValidationTests | 12 |
| V03SceneAdapterTickTests | 7 |
| SRP.F03.Tests | 3 |
| SRP.U01.Tests | 14 |
| **合计** | **98，全部 Passed** |

## 复现命令（PowerShell）

```powershell
# 注意：-runTests 不可与 -quit 同用，否则跳过测试
$unity = "E:\Unity\Editors\6000.4.9f1\Editor\Unity.exe"
$proj  = "D:\Agent\03-SRP\02-技术研发\04-Unity视觉\SRP-Weather-Visual"
$p = Start-Process $unity -PassThru -Wait -NoNewWindow -ArgumentList @(
  "-batchmode","-projectPath","`"$proj`"",
  "-runTests","-testPlatform","EditMode",
  "-testResults","`"D:\Coze\SRP\evidence\01_editmode_results.xml`"",
  "-logFile","`"D:\Coze\SRP\evidence\editmode_run4.log`""
)
$p.ExitCode   # 0 = 全通过；2 = 有失败
```
