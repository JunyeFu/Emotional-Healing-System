# SRP目标模块地图

> 本文件是新实现的模块、接口、依赖和验证入口。研究与统计规则以`00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/00_总控/13_IJHCI独立审稿攻击与升级裁定_v1.1.md`及同目录`protocol_authority_v1.1.json`为准。旧UDP v1.2、四维合成评分、TD呼吸圈和Spout链均为迁移输入，不是目标运行架构。当前目标能力均为`PLANNED_NOT_OBSERVED`，除非对应证据门已关闭。

## 1. 目标运行链

```text
M03 Device Capture
  -> M02 Python Session Core
       -> M04 Online Estimation
       -> M05 Runtime Contract + Immutable Records
            -> M06 Unity Participant Product
            -> M07 TD Operator Console
            -> M08 Offline Analysis

M01定义场景原生映射、抽象对照和测量材料。
M00管理研究版本、外部门禁、任务领取和证据。
M09验证跨模块行为并执行Level A/B/C。
M10形成论文、复现包、软件和展示成果。
```

Python是条件、顺序、时钟、协议、信号质量、事件、累计状态和落盘权威。Unity独立完成参与者完整体验。TD只读监控，不向Unity提供纹理、提示或状态。

## 2. 模块总览

| ID | 模块 | 主要目录 | 小接口 | 不承担 |
|---|---|---|---|---|
| M00 | 研究与数据治理 | `00-项目管理/`、`02-技术研发/07-数据治理/`、`work/` | 冻结基线、任务状态、L0-L5分级、跨阶段去重、隐私与资产许可门 | 运行时状态计算、随机分配 |
| M01 | 体验与测量设计 | `01-需求与设计/`、规划包`20_` | 四层候选语法、完整表示方案、SCCI操纵检查与条件中性测量 | 设备驱动、运行编排 |
| M02 | Python会话核心 | `02-技术研发/srp_session_core/` | manifest门、权威状态流、可靠控制服务和遥测发布门 | 设备协议细节、画面渲染、随机化生成 |
| M03 | 真实设备采集 | `02-技术研发/01-数据采集/` | 时间戳原始样本、设备状态、质量元数据 | 情绪结论、天气控制 |
| M04 | 在线交互状态估计 | `02-技术研发/02-信号处理/` | 目标/实际呼吸事件、质量、PF候选、累计更新 | 量表结论、正式统计 |
| M05 | 运行合同与记录 | `02-技术研发/05-通信协议/`、`02-技术研发/srp_session_store/` | manifest、控制/ACK、20Hz遥测、L0/L1追加、完整性与重放 | 会话状态推进、场景内部动画、TD界面 |
| M06 | Unity参与者制品 | `02-技术研发/04-Unity视觉/SRP-Weather-Visual/` | `ApplyTarget/Actual/Recovery/Fallback` | 随机化、阈值修改、TD依赖 |
| M07 | TD实验员操作台 | `02-技术研发/03-TouchDesigner/` | 只读遥测、人工标记、中止请求 | 参与者提示、直接控制Unity |
| M08 | 离线重建与分析 | 规划包`22_`、后续分析代码 | L0到L5、分析集、模型、图表、复现报告 | 覆盖L0、结果后改规则 |
| M09 | 验证与研究运行 | `03-测试与实验/`、规划包步骤7至10 | 单元、合同、重放、真机、Level A/B/C证据 | 越过外部门禁 |
| M10 | 论文与成果交付 | `04-成果与交付/`、规划包`25_` | 单篇IJHCI、复现包、构建、展示、权属材料 | 把计划写成已完成 |

## 3. 核心接口

### M03 DeviceSource

```text
connect(config) -> DeviceInfo
start(session_clock)
read() -> RawSample
status() -> DeviceStatus
stop()
```

PLUX respiBAN BLE与Polar H10是两个真实适配器。Mock和Replay是开发适配器；正式manifest必须拒绝它们。

### M02 SessionCore

```text
prepare(manifest, assignment, now_ns) -> CoreUpdate
apply_operator_request(request, now_ns) -> CoreUpdate
advance(now_ns) -> CoreUpdate
confirm_delivery(ack_or_receipt, now_ns) -> CoreUpdate
finish(reason, now_ns) -> SessionSummary
snapshot() -> SessionSnapshot
```

调用方不接触状态转换、时钟、控制序号和重试实现。P-01只读取X-01提供的分配，不生成随机化；相同manifest、分配和单调时钟输入必须产生相同轨迹。v2.1只开放固定顺序，阶段三冻结策略在合同升级前失败关闭。

### M05 Runtime Contract

- TCP 5010可靠控制通道传 `ControlEvent`、ACK、渲染回执和TD请求；
- UDP 5005/5006分别向TD和Unity发送20Hz自包含 `TelemetryFrame`；
- 所有消息包含schema版本、会话、序号和单调时间；
- TCP 5010、UDP 5005和UDP 5006已登记到 `D:\Agent\全局端口注册表.md`；
- 机器可读合同见 `02-技术研发/05-通信协议/contracts/runtime-contract-v2.1.schema.json`，完整语义见规划包 `21_真实设备与在线运行系统/06_目标运行接口_v2.md`。

### M05 Session Store

```text
append_manifest -> append_raw_packet/append_l1 -> checkpoint -> seal
verify -> iter_l0/iter_l1 -> replay_core
```

P-02通过`RecordingSessionCore`在控制发送前耐久提交P-01输入和输出，但不计算任何状态转换。中断恢复只保留和封存数据，不恢复原体验进度；L0/L1格式与证据入口见`02-技术研发/srp_session_store/README.md`。

### M06 SceneAdapter

```text
ApplyTarget(phase, progress)
ApplyActual(phase, progress, confidence)
ApplyRecovery(value, locked)
ApplyFallback(state, reason)
ResetModule(module_id, cue_mode)
```

四个场景和抽象对照共享该接口。场景内部参数和动画不泄露到Python或TD。

### M08 Rebuild

```text
validate_manifest(L0)
synchronize(L0) -> L1
detect_events(L1, annotations) -> L2
summarize(L2) -> L3
build_locked_sets(L3, questionnaires) -> L4
run_models(L4, analysis_plan) -> L5
```

每层输出输入哈希、代码提交、配置版本和排除原因码。

### M00 G-02 Governance

```text
normalize_phone -> check_and_reserve -> mark_exposed/release_before_exposure
privacy_lint_manifest -> P-01/P-02
scan_unity_assets -> Unity FormalBuildGate -> Z-01
```

G-02只对外返回不透明预约和审计ID。去重库、研究编号映射库和Windows凭据必须分离；正式专机、保留期限授权或Unity许可门任一未通过时失败关闭。实现与证据入口见`02-技术研发/07-数据治理/README.md`。

## 4. 依赖规则

1. M01和M05先冻结接口，再允许场景、设备、TD和离线实现并行。
2. M03只输出原始样本与设备元数据；M04不直接控制设备。
3. M02只通过M05合同与Unity/TD通信，不导入其内部代码。
4. M06必须在M07不存在时完成完整体验；禁止Spout运行依赖。
5. M07的人工标记和中止请求先进入M02并落盘，不能直接写M06状态。
6. M08只能读取冻结数据层，不从TD截图或Unity画面反推正式结果。
7. 旧 `calm_index`只允许兼容迁移，不进入条件、顺序、Gate或参与者级结果。
8. Level C前允许调整配置；正式构建和预注册锁定后，改变结果语义的修改必须停止对应招募并重新评估。

## 5. 验证层级

| 层 | 证据 | 解锁 |
|---|---|---|
| V0 | schema、合同测试、静态资源和配置检查 | 模块并行实现 |
| V1 | Python单元/性质测试、Unity Edit/Play Mode、TD离线fixture | 软件集成 |
| V2 | 记录重放、故障注入、Unity无TD运行、外部呈现延迟与多小时真机压力 | Level C候选构建 |
| V3 | Level A/B/C及冻结报告 | 正式阶段预注册 |
| V4 | 锁库、双分析、三重门和复现报告 | 论文结论 |

## 6. 当前实现事实

- 现有Python原型测试数量由根目录`pytest.ini`和当次测试报告确定，不在本文固化历史计数；
- Polar H10适配仍是未完成骨架，PLUX适配尚未实现；
- Unity现有资产和场景只作迁移参考；V-01、V-02与V-03已由真实团队第二人签收并转为`DONE`，不代表Unity运行完成；V-02签收对象为提交`3ebbdee`，签收提交为`c04a7be`；V-03最终候选`f09f0d5`经独立Agent复审及傅钧烨真实团队第二人复核均为`PASS`，签收提交为`e6d642e`；其7类78项资产台账仍未获得正式许可放行，`fade`仅冻结为U-03设计交接对象；F-03实现候选`a61eba6`经独立Agent复审和傅钧烨第二人确认后转为`DONE`，只提供可复现Unity环境、测试与Windows `DEV-REPLAY`构建底座；F-05候选`6760743`因证据哈希、v2.2 AC2覆盖和签收勾选缺口未通过严格审计，现于`codex/f-05-phase-v22`退回`IN_PROGRESS`修复；V-04保持`IN_PROGRESS`并等待团队总监H3确认；U-01、U-02、T-01、U-07和V-05仍有未关闭依赖，目标四层接口、两条件、实时通信和完整会话旅程仍未实现；
- TD现有 `.toe` 以呼吸引导为主，需要重构成只读操作台；
- UDP v1.2和Spout文档保留用于迁移审计，不能据此声称目标架构已完成。
- G-02已形成合成数据技术候选实现；正式专机检查和Unity资产许可仍为阻断状态，不得从测试通过推断正式使用能力。
- P-01会话核心与P-02追加存储已由真实团队第二人签收并转为`DONE`；该状态只关闭各自任务门，正式模式仍因X-01、G-02正式门、Unity客户端和真实输入链未闭合而失败关闭。
- 当前没有正式Unity独立构建、双真实设备完整链、外部延迟报告、Level A/B/C或参与者结果；这些均不得从任务状态推断。

## 7. 最小仓库验证

```powershell
Set-Location 'D:\Agent\03-SRP'
py -3.14 -m pytest '02-技术研发/01-数据采集/tests' '02-技术研发/02-信号处理/tests' '02-技术研发/05-通信协议/tests' '02-技术研发/07-数据治理/tests' '02-技术研发/tests' -q
git diff --check
git status --short
```

Python测试不能替代Unity画面、真机、TD只读行为和跨进程延迟证据。
