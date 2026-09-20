# U-02 ｜Unity｜四层 SceneAdapter 实现与降级

> 状态权属：遵循 `05_任务领取登记表.csv`；本任务为领取时锁定，实际改动与交付见本文件回填段与 `FILES.md` 中列出的项目权属路径。

## 领取记录

- 领取人：Codex(Grip)/小彬
- 工作分支：`codex/u-02-grip`
- 第二复核人：未指定
- 领取时间：2026-09-08

## 任务边界

- 工作域：Unity
- 优先级：W1
- 状态锁：`READY`
- 交付锁：FIXED
- 预估工作量：3 人日
- 前置依赖：F-03、F-05、V-03
- 核心技能：Unity+C#+接口实现+测试
- 涉及文件：以本任务目录下 `FILES.md` 为准

## 学习资料

- [L-UNITY Unity 手册（中文）](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework（中文手册）](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)

## 关键词

- SceneAdapter
- Target Actual Recovery Fallback 四层
- 降级
- 锁定
- 恢复

## 四个阶段约定

1. 先读取输入并建立失败不变 golden fixture
2. 只在最小模块里实现小步可验证改动
3. 每层异常不串权、不修改其他层状态
4. 完成后参数、文档与证据一并提交，再二次确认。

## 验收要求

- [x] AC1 每次状态变化只影响对应层，实际字段与 V-03 映射表同步
- [x] AC2 恢复层聚焦状态、再变化期间帧值只锁在合法更新路径
- [x] AC3 异常与恢复成功，也要保持背景层节律目标不变

## 交付证据

- [x] 接口测试
- [x] 参数快照
- [x] 层级隔离测试
- [x] 降级录像

## 架构约束

全程只读输入与输入帧，只通过同一个 SceneAdapter 扩展，不改侵入式模式，遵守契约 F-05 协议。

完成后必须暂停，等第二复核人复核。不得绕过证据路径产生复刻，只生成必要范围内的 commit，不自行 push。

## 完成回填

- 实际改动文件：
  - `Assets/Scripts/V03/`（D1：帧 DTO/JSON 解析/Validator/四只读 View/四态质量矩阵/SceneAdapter；D2：编排器 + Target/Actual/Recovery/Fallback 四层 Adapter + BackgroundPass 背景封印 + RecoveryLock + DegradationPolicy + ParameterBounds；D3：V03JsonFrameParser 解析修订、零串扰负测试、DevTools 降级演示驱动）
  - `Assets/Scripts/V03/DevTools/`：V03DegradationDemoDriver.cs（五阶段 IMGUI/命令行自动截图）、Editor/V03DemoBuild.cs（场景生成+构建）、SRP.V03.DevTools.Editor.asmdef
  - `Assets/V03DevTools/V03DegradationDemo.unity`：降级演示场景
  - 上述文件对应的全部 .meta（此前 D1/D2 漏提交，本次一并补齐）
- 验证命令与结果：
  - Unity 6000.4.9f1 batchmode EditMode：`Unity.exe -batchmode -projectPath <repo> -runTests -testPlatform EditMode -testResults <xml> -logFile <log>`
  - 结果 98/98 Passed（最新一次 start-time 2026-09-20 12:57:56Z，duration 7.30s，0 failed；加入演示脚本后编译无误）
  - 降级演示 exe 自动运行 EXIT=0，产出 120 帧（五阶段各 24 帧），逐帧多模态核验通过；ffmpeg 合成 MP4 成功
- 证据路径：
  - `D:\Coze\SRP\evidence\00_README.md`（证据总索引）
  - `01_editmode_results.xml`（98/98 全绿）、`02_parameter_snapshot.md`、`03_layer_isolation_report.md`
  - `04_degradation_demo/`：V03_degradation_demo.mp4（120帧/12fps/960×600）、frames/、player/V03DegradationDemo.exe、README.md
- commit：D1 `3d00447`、D2 `8ed6471`、D3 `9078bc1`
- push目标：已于 2026-09-20 经小彬批准后 push 至 `origin/main`（rebase 整合远端 2 个 commit，远端顶部 `9078bc1`；含更早领取 commit `874b5a8` 共 4 个）
- 剩余风险：
  - 录像为 960×600 演示级分辨率，非最终视觉精度，仅用于行为矩阵取证
  - 演示驱动/场景位于 DevTools 与独立目录，不参与正式构建（Editor-only asmdef 隔离）
  - 演示帧为 StubSource 合成帧；真实遥测源接入需按 V-03 契约另行联调
