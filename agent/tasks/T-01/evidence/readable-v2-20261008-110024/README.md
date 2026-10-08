# A主题可读性v2原生取证

2026-10-08，TD2025.32820。源为`../runtime/T01_ReadableBaseline.candidate.toe`，隔离副本运行后核对源字节未改变。候选为本目录`T01_Workbench_A.readable-v2.candidate.toe`，不覆盖历史签收工程。

## 画面

| 文件 | 核查内容 |
|---|---|
| [01等待](01-waiting.png) | 完整文字已出现；未知和缺失不冒充零值 |
| [02总览1280](02-overview-1280.png) | 1280×720布局，六统计及底栏完整可见，无总览滚动 |
| [03总览1600](03-overview-1600.png) | 1600×900布局，字号不变、列宽增加 |
| [04总览1920](04-overview-1920.png) | 1920×1080布局，字号不变、列宽增加 |
| [05明细](05-timing.png) | 两列表头、完整原字段 |
| [06明细滚动](06-timing-scrolled.png) | 原生滚轮移动正文，表头与底栏不移动 |
| [07审计](07-audit.png) | 居中未接入空状态，无假事件 |
| [08降级](08-degraded.png) | 琥珀色只用于对应状态单元 |
| [09不可用](09-unusable.png) | 红色与文字，不铺整页警告色 |
| [10长ID总览](10-long-id.png) | 会话ID缩略，其他关键标签不省略 |
| [11长ID明细](11-long-id-detail.png) | 完整ID换行；Text COMP允许选择复制 |
| [12断流](12-disconnected.png) | 顶栏明确末帧历史值，统计与原值保留 |
| [13恢复](13-final-overview.png) | 重新接收及累计重连次数 |

13张图逐张检查。三个标签通过SDK虚拟鼠标触发实际Panel Execute回调；不是直接调用页面切换函数。滚动前后`scrollv`不同，回执保留数值。所有原生错误回执为空。

重要：三种布局尺寸分别为1280×720、1600×900、1920×1080，但本机OP Viewer TOP实际导出13张PNG均为1280×720。未放大图片；后两张是较大布局在1280输出中的呈现，不是1600或1920原生像素截图。`capture-report.json`和逐图JSON分别记录两种尺寸。

## 验证与范围

主机专项：`py -3.14 -X utf8 -m pytest agent/modules/03-TouchDesigner/t01_telemetry_panel/tests agent/modules/03-TouchDesigner/f04_readonly_console/tests agent/tasks/T-01/execution/test_verify.py -q`，60 passed。

设计依据与指标见[设计说明](../../design/workbench-readable-v2.md)。工具栏四个图标及许可离线保存，按钮禁用，原生帮助名称注明未接入。输入是F-01 v2.2开发fixture，发送10 Hz，UI上限仍20 Hz。没有真实设备采集、T-02命令或研究准入证据；不修改DONE、签署或SVG。

复跑入口：`../../execution/capture_workbench.py`。首次输出先强制cook并等待字体呈现，再截图和保存。失败运行不计为通过，排错记录保留本地，不纳入本证据集。
