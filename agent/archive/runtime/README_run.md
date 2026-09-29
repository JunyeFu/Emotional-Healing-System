# SRP v2.1 最小闭环运行手册

> **LEGACY_DEV_ONLY：不可作为v2.1正式验收入口。** 本文件只保留10Hz、Mock、UDP v1.2和Spout迁移复现步骤。当前执行权威是`00_总控/13_IJHCI独立审稿攻击与升级裁定_v1.1.md`、`protocol_authority_v1.1.json`与`21_/06_目标运行接口_v2.md`。
>
> 正式链必须通过`LIVE_E2E`、Unity独立运行、20Hz遥测、可靠控制/ACK和真实来源门；本手册中的成功结果不得用于关闭这些门。

## 历史原型复现边界

本阶段只验收同机 Windows 闭环：

| 项 | 要求 |
|---|---|
| Python | 3.14，独立虚拟环境 |
| TouchDesigner | 正式版，接收 UDP `5005` |
| Unity | Unity 6000.4.9f1，D3D11/12 |
| Spout | 同机 Windows，NVIDIA/AMD，固定 Sender 名称 |
| 数据 | Python mock 优先，真实设备作为替换输入层 |

## 一键前检查

```powershell
python --version
git status -sb
```

目标结果：
- Python 为 3.14.x。
- Git 工作区干净或仅有本次明确修改。

## Python 环境

```powershell
Set-Location 'D:\Agent\03-SRP'
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r 02-技术研发\requirements.txt
pip install pytest
pip freeze > requirements-lock.txt
```

## Python 测试

```powershell
Set-Location 'D:\Agent\03-SRP\02-技术研发'
python -m pytest 01-数据采集\tests 02-信号处理\tests 05-通信协议\tests tests -q
```

通过标准：
- 所有测试通过。
- 失败时先修环境和字段契约，不先扩展功能。

## Mock 数据流

```powershell
Set-Location 'D:\Agent\03-SRP\02-技术研发'
python main.py --weather storm --duration 60
```

预期：
- UDP 发往 `127.0.0.1:5005` 和 `127.0.0.1:5006`。
- CSV 日志生成。
- 60 秒约 600 帧。

## TouchDesigner

打开：

```text
02-技术研发/03-TouchDesigner/呼吸引导.toe
```

最小监控台必须显示：
- `seq` 或帧序号。
- 接收频率，目标接近 10 Hz。
- `weather.type`。
- `calm_index`。
- `breath.phase`。
- `scores.breath_sync`、`scores.breath_depth`、`scores.hrv_coherence`、`scores.eda_calm`。
- Spout Sender 状态。

Spout Sender 固定名：

```text
SRP_BreathGuide_Main
```

## Unity

打开：

```text
02-技术研发/04-Unity视觉/SRP-Weather-Visual
```

最小响应字段：
- `weather.type`
- `weather.intensity`
- `calm_index`
- `breath.phase`
- `guidance.prompt`

验收方式：
1. 播放 `StormScene`。
2. 启动 Python mock。
3. 观察 Unity 场景强度随 `calm_index` 变化。
4. 切换 Heat/Snow/Fade 场景文件，确认可打开、可播放、主机制可见。

## 60 秒闭环成功标准

| 项 | 成功标准 |
|---|---|
| Python | 无异常退出，CSV 完整写入 |
| UDP | TD/Unity 均有连续数据 |
| TD | 监控数值和呼吸圈连续变化 |
| Spout | Unity 能接收固定 Sender 纹理 |
| Unity | 画面不黑屏，天气强度变化可见 |
| 日志 | CSV 可重新打开并用于画图 |

## 故障排查

| 现象 | 优先排查 |
|---|---|
| TD 收不到包 | 端口 `5005`、地址 `127.0.0.1`、防火墙 |
| Unity 收不到包 | 端口 `5006`、Play Mode、`UDPReceiver` 是否挂载 |
| Unity 收到但画面不动 | `WeatherController` 是否真正读取 `weather.type` 和 `weather.intensity` |
| Spout 无接收 | Sender 名称、D3D11/12、显卡条件 |
| CSV 列错 | 先改字段冻结表，再改 Python/TD/Unity |
