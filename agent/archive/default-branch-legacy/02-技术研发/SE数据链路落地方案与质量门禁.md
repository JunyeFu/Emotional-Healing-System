# SE 数据采集与传输链路落地方案

> 负责人范围：可穿戴设备数据收集、信号处理、评分模型、UDP/OSC/CSV、TD/Unity 数据传输链路。

## 1. 职责边界

你的核心交付不是“更复杂的状态识别”，而是把设备输入稳定转换成可被 TD 和 Unity 消费的数据流。

| 范围 | 你负责 | 不由你主责 |
|---|---|---|
| 设备层 | Mock、Polar H10、呼吸带、EDA 通道接入与状态标记 | 设备采购决策之外的商务流程 |
| 数据层 | 10Hz RawFrame、ProcessedFrame、ScoreFrame | Unity 美术表现细节 |
| 模型层 | 四维评分与 `calm_index` | 四天气自动归类 |
| 传输层 | UDP `5005/5006`、OSC、CSV 日志 | TD/Unity 内部视觉编排 |
| 验收层 | 字段契约、测试、压测、异常记录 | 被试招募与问卷主设计 |

## 2. 总体目标

阶段5-6 的 SE 目标：

```text
可穿戴或 mock 输入 → 10Hz 标准帧 → 四维评分 → UDP v1.2 → TD/Unity → CSV 可复盘
```

成功定义：

- 同机 60 秒闭环稳定运行。
- TD 和 Unity 读取同一份 UDP JSON。
- CSV 字段固定、可复盘、可画图。
- 任一设备缺失时系统降级运行，不崩溃。
- 所有输出只表达交互状态估计，不作严肃判断。

## 3. 数据链路架构

```text
Device / Mock
  ↓
RingBuffer per channel
  ↓ 10Hz
FrameClock / DeviceManager
  ↓
RawFrame
  ↓
SignalPipeline
  ↓
ProcessedFrame
  ↓
ScoringModel
  ↓
ScoreFrame
  ↓
UDPSender → TD:5005
          → Unity:5006
CSVLogger → experiment logs
```

## 4. 分阶段落地

### A. 环境基线

| 任务 | 操作 | 验收 |
|---|---|---|
| Python 版本 | 建立 Python 3.14 `.venv` | `python --version` 输出 3.14.x |
| 依赖安装 | `pip install -r 02-技术研发/requirements.txt` | 无安装失败 |
| 测试工具 | `pip install pytest` | `python -m pytest --version` 可用 |
| 锁定依赖 | `pip freeze > requirements-lock.txt` | 锁文件入库或归档 |

推荐命令：

```powershell
Set-Location 'D:\Agent\03-SRP'
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r 02-技术研发\requirements.txt
pip install pytest
pip freeze > requirements-lock.txt
```

### B. Mock 数据先行

Mock 是本项目的默认验收输入。真实设备未稳定前，不阻塞闭环。

| 任务 | 文件 | 验收 |
|---|---|---|
| 四天气 mock | `01-数据采集/mock_data.py` | storm/heat/snow/fade 均可生成 |
| 10Hz 节奏 | `main.py` | 60 秒约 600 帧 |
| 相位输出 | `breath.phase` | inhale/hold/exhale 连续变化 |
| 强度输出 | `weather.intensity` | 与 `calm_index` 反向变化 |

运行：

```powershell
Set-Location 'D:\Agent\03-SRP\02-技术研发'
python main.py --weather storm --duration 60
```

### C. 真实设备接入

真实设备按“可替换输入层”处理，不改变下游字段契约。

| 通道 | 优先输入 | 回退输入 | 输出字段 |
|---|---|---|---|
| 呼吸 | 呼吸胸带 | ECG 推导或 mock | `breath.*`、`scores.breath_sync`、`scores.breath_depth` |
| 心电 | Polar H10 | mock | `cardiac.*`、`scores.hrv_coherence` |
| EDA | EDA 腕带 | 中性值或 mock | `eda.*`、`scores.eda_calm` |

接入规则：

- 每个设备独立标记 `connected` / `no_signal` / `mock`。
- 设备缺失时对应评分回落到中性值，不让主循环崩溃。
- 所有设备状态写入 `meta.devices` 和 `meta.signal_quality`。
- 不因真实设备未到位而阻塞 TD/Unity 验收。

### D. 信号处理与评分

四维评分保持固定：

| 维度 | 输入 | 输出 | 失败回退 |
|---|---|---|---|
| `breath_sync` | 呼吸率 vs 目标频率 | 0-100 | 50 |
| `breath_depth` | 呼吸振幅 vs 目标振幅 | 0-100 | 50 |
| `hrv_coherence` | RMSSD vs 目标值 | 0-100 | 50 |
| `eda_calm` | EDA tonic 相对基线 | 0-100 | 50 |

门槛：

- 所有评分必须裁剪到 `0-100`。
- `calm_index` 必须裁剪到 `0-100`。
- `weather.intensity` 必须裁剪到 `0-1`。
- 任一输入为 NaN/None 时不能进入 UDP。

### E. UDP 字段契约

唯一真相来源：

```text
02-技术研发/05-通信协议/UDP字段冻结_v1.2.md
```

发送端必须保证：

- `version = "1.2"`。
- `timestamp`、`meta.frame_id` 每帧存在。
- `weather.type` 只允许 `storm/heat/snow/fade`。
- TD 和 Unity 收到的是同一份 payload。
- JSON 单帧尽量小于 1500 bytes。

### F. CSV 日志

CSV 是实验复盘证据，不能只作为调试输出。

最低字段：

```text
timestamp,frame_id,weather_type,weather_intensity,weather_trend,calm_index,
breath_sync,breath_depth,hrv_coherence,eda_calm,
breath_phase,breath_rate,breath_amplitude,hr,rmssd,eda_tonic,
source_breath,source_cardiac,source_eda,pipeline_latency_ms,operator_mark
```

规则：

- 文件名使用 `SRP_P{ID}_{date}_{scene}_v2p1_csv`。
- mock 调试日志使用 `mock_{weather}_{timestamp}.csv`。
- 字段顺序固定。
- 多余字段应显式失败，不静默吞掉。
- 每次实验结束后立即打开检查行数和列名。

## 5. TD/Unity 联调职责

### 5.1 TouchDesigner 对接

SE 交付给 TD 的内容：

| 项 | 要求 |
|---|---|
| 端口 | UDP `5005` |
| 数据格式 | JSON UTF-8 |
| 频率 | 10Hz |
| 必显字段 | `frame_id`、四维评分、`calm_index`、`weather.type`、`breath.phase` |
| 监控重点 | 收包频率、缺包、字段空值、Spout 状态 |

TD 验收时你要在场确认：

- `frame_id` 连续增加。
- TD 显示频率接近 10Hz。
- `calm_index` 与四维评分不为空。
- `breath.phase` 能驱动呼吸圈节律。

### 5.2 Unity 对接

SE 交付给 Unity 的内容：

| 项 | 要求 |
|---|---|
| 端口 | UDP `5006` |
| 天气字段 | `weather.type` |
| 强度字段 | `weather.intensity`、`calm_index` |
| 引导字段 | `breath.phase`、`guidance.prompt` |
| 调试字段 | `meta.frame_id`、`meta.pipeline_latency_ms` |

Unity 验收时你要确认：

- Unity Console 显示正在监听 `5006`。
- `weather.type` 切换后场景或控制器状态一致。
- `weather.intensity` 改变时主视觉机制响应。
- Unity 不依赖旧字段 `guidance.circle_radius`。

## 6. 质量门禁

### SE-G0：环境门禁

| 检查项 | 类型 | 通过标准 |
|---|---|---|
| Python 版本 | Blocker | 3.14.x |
| 依赖安装 | Blocker | requirements 安装成功 |
| pytest 可用 | Blocker | `python -m pytest --version` 成功 |
| Git 状态 | Advisory | 开始联调前工作区清楚 |

### SE-G1：字段契约门禁

| 检查项 | 类型 | 通过标准 |
|---|---|---|
| 字段冻结表存在 | Blocker | `UDP字段冻结_v1.2.md` 已更新 |
| `udp_sender.py` 版本 | Blocker | 输出 `version = "1.2"` |
| 必需字段完整 | Blocker | 自动测试覆盖 |
| 天气枚举合法 | Blocker | 仅四种天气 |
| JSON 大小 | Advisory | 单帧 < 1500 bytes |

### SE-G2：单元测试门禁

| 检查项 | 类型 | 通过标准 |
|---|---|---|
| 数据采集测试 | Blocker | `01-数据采集/tests` 通过 |
| 信号处理测试 | Blocker | `02-信号处理/tests` 通过 |
| 通信测试 | Blocker | `05-通信协议/tests` 通过 |
| 压测测试 | Advisory | `tests/test_stress_test.py` 通过 |

最低新增测试建议：

| 测试 | 目的 |
|---|---|
| `test_udp_payload_required_keys` | 防止字段缺失 |
| `test_weather_type_enum` | 防止天气字段漂移 |
| `test_scores_are_bounded` | 防止评分越界 |
| `test_no_nan_in_payload` | 防止 NaN 进入 JSON |
| `test_csv_header_fixed` | 防止 CSV 列漂移 |
| `test_frame_id_increases` | 防止序号异常 |

### SE-G3：60 秒闭环门禁

| 检查项 | 类型 | 通过标准 |
|---|---|---|
| 发送帧数 | Blocker | 60 秒约 600 帧 |
| UDP 错误 | Blocker | 无连续发送失败 |
| TD 接收 | Blocker | 5005 连续接收 |
| Unity 接收 | Blocker | 5006 连续接收 |
| CSV 写入 | Blocker | 行数与运行时长匹配 |
| 主循环稳定 | Blocker | 无崩溃、无 NaN |

### SE-G4：设备降级门禁

| 场景 | 通过标准 |
|---|---|
| 仅 mock | 完整闭环可运行 |
| 无呼吸带 | 呼吸 source 标记为 `none` 或回退来源 |
| 无 EDA | `eda.source=none`，`eda_calm` 中性 |
| 无 Polar H10 | `cardiac.source=none`，`hrv_coherence` 中性 |
| 设备断开 | 不中断主循环，meta 状态更新 |

### SE-G5：实验前门禁

| 检查项 | 类型 | 通过标准 |
|---|---|---|
| 2 人预实验日志模板 | Blocker | 文件命名规范可执行 |
| 异常记录表 | Blocker | `operator_mark` 或独立异常表可用 |
| 端到端延迟记录 | Advisory | `pipeline_latency_ms` 可写入 CSV |
| 术语扫描 | Blocker | 项目 Markdown 无禁用词 |
| 备份机制 | Advisory | 实验 CSV 当天备份 |

## 7. 每日执行清单

### 每天开始

```powershell
git status -sb
.\.venv\Scripts\Activate.ps1
python --version
```

### 每次改 Python 后

```powershell
cd 02-技术研发
python -m pytest 01-数据采集\tests 02-信号处理\tests 05-通信协议\tests tests -q
```

### 每次联调前

```powershell
python main.py --weather storm --duration 60
```

检查：

- 终端无异常。
- TD 收到 5005。
- Unity 收到 5006。
- CSV 有输出。

### 每天结束

- 更新看板状态。
- 归档当天日志、截图、问题。
- 如有字段变化，先更新 `UDP字段冻结_v1.2.md`。
- commit 前跑 `git diff --check`。

## 8. 异常处理

| 现象 | 第一排查 | 处理 |
|---|---|---|
| Python 启动失败 | venv、依赖、路径 | 先恢复环境，不改业务代码 |
| TD 收不到包 | 5005、防火墙、地址 | 固定 `127.0.0.1` |
| Unity 收不到包 | 5006、Play Mode、脚本挂载 | Console 打印端口和 frame_id |
| CSV 空文件 | logger open/write/close | 增加最小写入测试 |
| 评分异常跳变 | 输入 NaN、窗口太短 | 回退中性值并记录 source |
| 字段不一致 | 文档与代码漂移 | 以字段冻结表为准 |

## 9. 交付物

| 交付物 | 路径 | 完成标准 |
|---|---|---|
| 运行手册 | `README_run.md` | 新人按步骤能跑 mock 闭环 |
| 字段冻结表 | `02-技术研发/05-通信协议/UDP字段冻结_v1.2.md` | Python/TD/Unity/CSV 一致 |
| SE 方案 | 本文件 | 覆盖采集、处理、传输、门禁 |
| 测试结果 | `00-项目管理/03-进度跟踪/开发进度打卡表.md` 或日志目录 | 有日期、命令、结果 |
| CSV 样例 | `03-测试与实验/实验数据/` | 可读、列完整 |
| 压测记录 | `03-测试与实验/04-测试报告/` | 60 秒结果可复核 |

## 10. 当前最高优先级

1. 恢复 Python 3.14 + pytest 环境。
2. 补 UDP payload 和 CSV 字段测试。
3. 修复/确认 `WeatherController` 接收 v1.2 字段后的响应链。
4. 完成 60 秒 Python → TD → Unity → CSV 闭环记录。
5. 跑 2 人预实验前，把设备缺失降级逻辑确认清楚。
