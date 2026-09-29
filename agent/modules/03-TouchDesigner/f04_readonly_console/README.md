# F-04 模块化图形化只读操作台

本目录保留 F-04 已签收的 TouchDesigner 2025.32820 静态基线。它使用本地静态
fixture 演示 10 个页面与 5 个确定性场景，不是正式设备消费者，也不产生
运行控制。所有页面持续显示 `READ ONLY / DEV-REPLAY / NOT LIVE`。

## 模块边界

- `ConsoleShell` 只负责本地页面导航、场景切换和只读状态栏。
- 页面只消费不可变 `ConsoleSnapshot`；`StaticFixtureAdapter` 是 F-04 唯一启用
  的数据适配器。
- `telemetry` 复用 TelemetryFrame v2.1 的 29 个合同字段；`display_only` 仅供
  本地显示，不得进入正式线格式。
- UDP 5005 仅保留停用的 `T-01 NOT ACTIVE` 占位。人工标记与中止仅显示
  `enabled=false / T-02 NOT ACTIVE`，不存在发送回调。
- 上述标识仅描述F-04壳内未启用的能力，不表示项目T-01未完成。

## 图形结构

- 呼吸页使用 `DAT to CHOP -> Select/Math CHOP -> OP Viewer TOP` 显示原始与
  滤波双通道曲线。
- 设备、质量、相位、周期、时钟、降级和日志页使用状态卡、色块、条形指示
  或时间轨迹；人工操作页使用明确的禁用控件。
- 10 个页面按钮和 5 个场景按钮只修改本地显示状态，没有网络、文件或运行
  控制副作用。

## 构建与验证

从仓库根目录运行：

```text
py -3.14 agent/tasks/F-04/execution/verify_host.py
```

TD执行脚本已迁入 [F-04执行层](../../../tasks/F-04/execution/README.md)。
新候选保存在任务outputs，新主机/TD证据保存在任务evidence；不覆盖本目录的历史签收制品。
当前主机清单的 `fixture_sha256_policy=raw_bytes` 表明哈希使用原始字节，
历史签收里的Git/LF规范化哈希保持原有含义，不直接与CRLF字节哈希混比。

机器验收结果记录于 `F-04_技术验收记录.md`。首轮独立总监审计与整改映射
记录于 `F-04_团队总监首轮审计整改记录.md`。用户授权的独立团队总监已在
精确候选上完成二轮实机复审并签署 `PASS`，结论记录于
`F-04_独立团队总监二轮复审签收报告_已签署.md`；F-04 状态为 `DONE`。

## 证据边界

静态场景与合成波形只证明页面、模块边界和只读权限可复现，不证明真实设备
采集、信号质量、交互状态估计有效性、正式 20 Hz 消费、请求处理、LIVE_E2E、
科学有效性或人工验收。
