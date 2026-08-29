# F-04 模块化图形化只读操作台

本目录是 F-04 的 TouchDesigner 2025.32820 升级候选。它使用本地静态
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
py -3.14 -m pytest 02-技术研发/03-TouchDesigner/f04_readonly_console/tests/test_f04_console.py -q
py -3.14 02-技术研发/03-TouchDesigner/f04_readonly_console/f04_node_plan.py
```

在 TouchDesigner 2025.32820 中执行 `build_f04_touchdesigner.py`。构建器只替换
`/project1/F04_ReadonlyConsole`，保存正式 `.tox/.toe`，并在工程完成 cook 后
生成 10 张 GOOD 页面截图和 4 张其他场景差异截图。重新打开正式 `.toe` 后执行：

```text
exec(open(r'D:\Agent\03-SRP-f04-worktree\02-技术研发\03-TouchDesigner\f04_readonly_console\verify_f04_touchdesigner_reopen.py', encoding='utf-8').read())
```

当前机器验收结果记录于 `F-04_技术验收记录.md`。F-04 处于 `IN_REVIEW`；
AC1–AC6 已通过机器门，AC7 必须由傅钧烨独立操作并签署 PASS/FAIL。

## 证据边界

静态场景与合成波形只证明页面、模块边界和只读权限可复现，不证明真实设备
采集、信号质量、交互状态估计有效性、正式 20 Hz 消费、请求处理、LIVE_E2E、
科学有效性或人工验收。
