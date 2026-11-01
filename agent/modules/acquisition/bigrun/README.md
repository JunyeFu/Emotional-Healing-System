# BigRun Team 单设备候选

状态：`DEVELOPMENT_UNVERIFIED`。一条 BLE 连接采集 ECG、RR、HR、三轴 ACC；呼吸为 ACC 衍生代理，不是已验证的独立呼吸测量。本次按用户授权准备替代设备候选，不更改 D-01/D-02 的正式设备、注册状态、已冻结协议或签收。

## 入口与环境

- 命令入口：[bigrun.cmd](../../../runtime/bigrun.cmd)；Python 入口：[bigrun.py](../../../runtime/bigrun.py)。
- Python 3.14 专用环境：`agent/local/venvs/bigrun/`；数据默认放在 Git 忽略的 `agent/local/artifacts/bigrun-preflight/`。
- 环境不存在时，在仓库根执行：

```powershell
python -m venv agent/local/venvs/bigrun
agent/local/venvs/bigrun/Scripts/python.exe -m pip install -r agent/modules/acquisition/bigrun/requirements.txt
agent/runtime/bigrun.cmd --help
```

本机已创建环境并安装依赖。2026-10-20 已有短时真实通知记录，但持续连接和真实双通道显示尚未通过；见[验证日志](../../../work/codex-verification-log.md)。裸双击 CMD 只显示命令帮助，不会自动连接。

## 已接入的项目接口

1. `BigRunDriver` 实现现有 `DeviceDriver` 生命周期，单连接分发多种通知；`drain_frame()` 返回项目 `RawFrame`，ECG 保留原生批次，呼吸保留代理批次。
2. 原始字节、主机单调接收时间、全局包序号、原生批次样本数通过现有 `SessionArchive.append_raw_packet()` 写入 P-02。ECG ADC 整数、RR 整数和两组 XYZ 均不丢弃；ECG 包头/原设备 RR 序号仍可从原字节重建。
3. 未知、异常长度、零样本及配置通知以原字节十六进制写入 P-02 L1 `bigrun_notification`，不猜测、补零或当成有效样本。
4. 显式模式先查询 ECG/SR/XO，只写不匹配项并再次读回；写命令 ACK 不等于模式验证。回调中的记录失败传回主循环，断连终止本次采集，不静默换 mock 或自动续接。
5. 可选 `--frames` 导出候选 RawFrame JSONL；`capture --td` 或 [start-td-bigrun.cmd](../../../runtime/start-td-bigrun.cmd)将专用只读预览送到[BigRun TD工程](../../touchdesigner/t01_telemetry_panel/design/bigrun-workbench.md)。不是正式20Hz UDP，不进入旧Mock、SessionCore或Unity。旧SignalPipeline不作为正式呼吸链。

原始源名：`bigrun_team_ecg/rr/acc/hr`。存储层允许这些源名只表示可记录，不表示正式运行准入。候选归档 `formal_capable=false`；真实通知用 `source_policy=real`，合成测试用 `mock/replay`，不混淆来源。

`RawFrame.signal_validity['resp']` 始终为 false，`breath_phase='unknown'`、深度为空。即使有代理波形也不自动宣称呼吸事件已识别。ECG validity 仅表示有新原始样本，不代表 SQI 合格。Frame 时间为主机单调秒；缺少真实采样时钟时不能混用为已同步的正式帧。

## APK 核对后的连接流程（2026-10-20）

依据用户提供 ECTRI APK 的 ManDevice 路径独立调整，详见[分析与接入记录](../../../work/2026-10-20_ectri-ble-integration.md)：

1. 按指定地址显式扫描，使用扫描得到的 BLEDevice；Windows 设置 `use_cached_services=False`，不增加强制配对。
2. 等待私有通知订阅完成，再串行发送日期、设备信息、电量、ECG速度/信号/采样配置读取，随后查询模式并启动采集。
3. `observe` 不写模式；显式模式仅写差异项。模式切换可能重启设备，若断连则本次归档中止，重新唤醒后由操作者另开采集，不能自动续接实验。
4. 控制台及 TD 状态包带 `connection_phase`；P-02 L1 `bigrun_connection` 保存连接/启动状态和失败原因。`connected_gatt`、`waiting_for_data` 不表示已收到有效信号，只有实际数据包推动 `receiving`。

APK 的 `Authenticated` 是订阅完成后的应用状态，未发现该路径要求私钥握手或周期保活。没有扫描到广播仅记为 `scan/BIGRUN_NOT_ADVERTISING`，不推断设备拒绝或硬件损坏。订阅前的 GATT Unreachable 不能靠订阅后的初始化命令解释。初次复测优先 `--mode observe`，避免把模式重启与链路故障混在一起。

## 设备到手后的实测步骤

### 1. 登记与首次采集

- 登记外壳型号、硬件/固件版本、胸带尺寸和佩戴位置；向商家索取同版本说明书、ECG/ACC 输出率、RR 单位、并发能力和原始数据协议。当前没有核实到型号专用官方校准文档。
- 按厂商佩戴说明安装；先断开手机 App 等可能占用蓝牙连接的客户端。
- 只在准备好后执行以下命令，扫描结果由操作者选择，不自动连接附近设备：

```powershell
Set-Location D:\Agent\srp
agent/runtime/bigrun.cmd scan
$address = Read-Host '输入刚才确认的 BigRun 蓝牙地址'
agent/runtime/bigrun.cmd capture --address $address --mode observe --seconds 60
```

`observe` 不修改模式位，但仍查询配置并发送日期/采集启动命令；它不是完全被动嗅探。日期同步不被当成样本时钟。控制台 `ARCHIVE=...` 是此次会话目录；捕获期间不确认准备、不开始实验。

### 2. 验证模式与并发，不先猜采样率

```powershell
agent/runtime/bigrun.cmd capture --address $address --mode ecg --seconds 180
$session = Read-Host '粘贴这次 ARCHIVE 目录'
agent/runtime/bigrun.cmd inspect --session $session
```

- 逐项记录 ECG、ACC、RR、HR 的通知/样本数、配置读回和 ECG/ACC 同秒交错情况。host_rate_estimate_hz 仅为主机观察估计，不是设备时钟验证。
- 再用 `--mode hrv` 另开一次归档，确认原生 RR 是否只在该模式出现。没有 RR 时保留缺失；可另用 ECG R 峰计算 RR，但不能说成“原生 RR 已验证”。
- 实测断开设备、正常结束和 Ctrl+C；检查归档可读、未知通知保留、断流不补数。每次重连创建新归档。
- 确认数据率、分包及丢包语义后才输入下面的名义值。禁止把内部采样率、商品宣传值、`ecg_sr_reported` 字段或测试样例直接当作蓝牙输出率。

### 3. 导出与建立独立参考

```powershell
$ecgHz = [double](Read-Host '输入已核对的 ECG 蓝牙输出率 Hz')
$accHz = [double](Read-Host '输入已核对的 ACC 蓝牙输出率 Hz')
agent/runtime/bigrun.cmd export --session $session --out agent/local/artifacts/bigrun-fit --ecg-hz $ecgHz --acc-hz $accHz
```

导出目录须不存在。包括 `ecg.csv`、`acc.csv`、`rr.csv`、`hr.csv` 和 `export.json`。ECG/ACC `time_s` 是依据用户输入率和首包构造的**名义样本索引时间**，未修复丢包、未校正时钟漂移。RR 的 `time_s` 只是包接收时间，不是每个心搏时间；`value` 单位不猜测。所有原始包仍在 P-02。

准备同步参考 ECG/可靠 R 峰记录及参考呼吸带。参考文件来自独立设备，不使用引导圈 G 或算法自己的预测作真值；用共同时间基准/同步标记确定偏移，不能用反复平移周期曲线冒充时钟校准。参考 CSV 最少格式：

```text
reference-beats.csv: time_s
reference-resp.csv:  time_s,value
```

`time_s` 统一为秒，且与候选导出数据对齐；参考呼吸文件为均匀采样，缺失或断点不跨越插补。脚本只读取参考文件，不包含参考设备驱动。当前不自动估计设备时钟漂移或参考偏移。

### 4. 心率/心搏时间校准检查

```powershell
agent/runtime/bigrun.cmd calibrate-heart --ecg agent/local/artifacts/bigrun-fit/ecg.csv --reference-beats reference-beats.csv --polarity 1 --reference-delay-s 0 --out agent/local/artifacts/bigrun-fit/heart-profile.json
```

极性需根据实际 ECG 核对，倒置时改为 -1。默认 0.1 秒仅是技术匹配窗口，不是研究验收阈值。脚本调用 NeuroKit2 清理/检测 R 峰，输出漏检、多检、R 峰时差、相邻匹配 RR 误差、平均心率及未校正 RMSSD；不填补漏搏，不用静态增益“调整”HRV，不标记自动通过。

RR 私有整数的 ms/1/1024s 等单位、原始 ECG 电压换算仍未校准；不能直接将标准 BLE HR 服务的单位套用到私有通知。报告中的 RMSSD 只是未完成质量筛选的探索数值。

### 5. 呼吸投影标定与独立验证

单独采集至少数分钟的同步标定数据，覆盖自然呼吸和项目慢呼吸；另录一段独立验证数据，包含自然呼吸、目标慢呼吸、舒适短暂停留/补吸和轻微体动，保存独立事件标注。验证段不要从训练段切一份相同数据或仅改文件名。

```powershell
agent/runtime/bigrun.cmd calibrate-resp --acc agent/local/artifacts/bigrun-fit/acc.csv --reference reference-resp.csv --acc-hz $accHz --reference-delay-s 0 --out agent/local/artifacts/bigrun-fit/resp-profile.json
agent/runtime/bigrun.cmd validate-resp --acc agent/local/artifacts/bigrun-validation/acc.csv --reference validation-resp.csv --profile agent/local/artifacts/bigrun-fit/resp-profile.json --out agent/local/artifacts/bigrun-validation/resp-report.json
agent/runtime/bigrun.cmd validate-heart --ecg agent/local/artifacts/bigrun-validation/ecg.csv --reference-beats validation-beats.csv --profile agent/local/artifacts/bigrun-fit/heart-profile.json --out agent/local/artifacts/bigrun-validation/heart-report.json
```

- 默认呼吸带通 0.04–0.8Hz 是开发候选范围，不是冻结参数；二阶 SciPy SOS 因果滤波可逐批连续运行。丢弃起始 `2/低截止频率` 秒，后面至少再有同样时长的数据；默认各 50 秒。
- 拟合三轴投影、截距及相对幅度；输出单位是参考标准差，不是 g、毫伏或体积。参考延迟为人工提供：`proxy(t)` 对比 `reference(t-delay)`，不会在实时预览中偷偷挪动时间。
- 验证只使用已冻结参数，不再优化轴向、增益或延迟；拒绝直接复用同路径标定文件。仅输出波形相关、归一化误差、呼吸频率误差，不据此宣布事件识别通过。
- 重新佩戴、换姿态和体动后的可迁移性要分别检查。平坦 ACC 或参考、太短、非有限值、明显采样间断会报错，不生成“成功校准”。

### 6. 持续预览，仍由你手动开始实验

```powershell
agent/runtime/bigrun.cmd capture --address $address --mode ecg --ecg-hz $ecgHz --acc-hz $accHz --heart-profile agent/local/artifacts/bigrun-fit/heart-profile.json --resp-profile agent/local/artifacts/bigrun-fit/resp-profile.json --frames agent/local/artifacts/bigrun-live-frames.jsonl
```

省略 `--seconds` 即持续采集，Ctrl+C 停止。优先显示新鲜 HR 包，缺少 HR 包且有心率 profile 时用最近 ECG 窗估计；呼吸预热后显示代理值。屏息、吸呼相位、补吸及 SQI 保持 unknown，不自动启动/确认/暂停实验。

这一步验证的是候选软件入口，不是 TD/Unity 正式运行接线。实机采集、同步质量、参考对照和 D-01/D-02/S-01/S-02 所需复核齐备后，再承接正式协议/运行集成；不得修改 `signal_validity` 强行放行。

## 当前验证边界

| 项目 | 状态 |
|---|---|
| 上游示例包解码、两组 ACC、原始整数与未知包保存 | 合成测试通过 |
| P-02 追加、封存、读取和导出 | 软件集成测试通过 |
| 模式读回、记录异常与断连处理 | 替身测试，不是真机验证 |
| 显式扫描、Windows无缓存参数、APK初始化顺序、模式ACK隔离与失败分层 | 替身测试通过；本轮未连接硬件 |
| NeuroKit2 心搏检查、因果滤波分块一致性、冻结参数验证命令 | 合成数据测试通过 |
| 本机 UUID 和短时 ECG/ACC/RR/HR 通知 | 已观察；持续并发与稳定性未通过，不能记为完整验收 |
| 输出率、设备时钟、原设备序号/丢包语义、ADC/RR 物理单位 | UNVERIFIED |
| 实际心率/HRV误差、呼吸频率/波形、跨人和重新佩戴 | NOT_RUN |
| 吸呼、停留、补吸事件识别器及其延迟/SQI | NOT_IMPLEMENTED / NOT_RUN |
| 正式 TD/Unity 遥测、闭环、研究准入及真人签收 | NOT_RUN；未改变原状态 |

测试：`agent/local/venvs/bigrun/Scripts/python.exe -m pytest agent/modules/acquisition/tests agent/modules/tests/session_store -q`。测试文件内的波形/协议样例全部是 synthetic，不作为真实设备证据。

## 来源

本候选按公开协议行为独立重写，不将社区实现称为官方 SDK：

- [原逆向工程与协议](https://github.com/zHElEARN/brt-reverse)，核对时间 2026-10-18；仅适用其已观察到的协议，其他固件待实机确认。
- [Bleak 官方通知及连接接口](https://bleak.readthedocs.io/en/latest/api/client.html)：回调不自带逐样本设备时间。
- [SciPy sosfilt 官方帮助](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfilt.html)：状态连续的分块因果滤波。
- [NeuroKit2 ECG 官方帮助](https://neuropsychology.github.io/NeuroKit/functions/ecg.html)：心搏检测和显式采样率；本实现不直接将 ecg_rsp 的默认范围当作已验证呼吸模型。
