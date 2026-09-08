# T-01 工作台视觉重建 v2

日期：2026-09-08。交付类型：AI生成设计预览与布局规格，待TouchDesigner实现。原T-01签收范围保持原记录。

## 任务依据与问题

T-01任务负责UDP5005遥测、设备质量、时钟、序号、断流与异常恢复的只读显示。原图`../evidence/touchdesigner/screenshots/fixture_good.png`使用大字号整页文本，右侧步骤与进度被裁切，底部降级内容超出画面。重建采用独立区域和列对齐。

## 固定布局

建议画布1600×900，外边距28px；最低验证尺寸1280×720。正文18至24px，标题28px，辅助信息16px。文本使用原生组件绘制，生成图片仅作设计参考，不承载实时数据。

| 区域 | 内容 | 约束 |
|---|---|---|
| 顶栏 | 工作台名称、T-01只读、链路状态、开发回放标记 | 状态文字与标题分区；WAITING灰色，LIVE绿色，DISCONNECTED红色 |
| 会话行 | session_id、runtime_mode、模块、段、schema_version | 长会话ID独占可换行区域；完整值可从详情读取；字段缺失显示破折号 |
| 左中区 | 呼吸与心电设备状态、两项SQI | 青绿与琥珀色区分来源；质量条不与数值重叠；未知值为空条 |
| 右中区 | 目标与实际的周期、步骤、相位、进度 | 同行对照；步骤ID使用合同原值，不由相位推断 |
| 左下区 | 帧龄、source_to_received_ms、received_to_sent_ms、clock_offset_ns、clock_drift_ppm、sync_uncertainty_ns | 数值与单位分列；不将本地帧龄标成端到屏幕延迟 |
| 右下区 | accepted_frames、lost_frames、duplicate_frames、out_of_order_frames、invalid_frames、reconnect_count | 六列等宽；超长数字换用详情行，保留完整数值 |
| 状态带 | fallback_state、fallback_reason、frame_seq、last_error | 原因与错误允许换行；不覆盖上方统计 |
| 页脚 | 数据新鲜度提示、127.0.0.1:5005、接口v2.2、20Hz上限 | 区分配置值和收到的数据值 |

模块、段仅在收到的合同数据提供对应字段时显示，否则保持缺失。无遥测时设备状态为未知；断流时显示断流并标明末帧为历史值。dev_replay标记始终可见。当前输入没有原始波形，设计不生成装饰性波形。

## 实施与验收

1. 复用`t01_telemetry.py`的不可变快照与统计逻辑；将`ConsoleShell/panel_text`整页文本改为分区原生显示组件。
2. 用独立网格设置位置、尺寸和文本区域；质量条与标签分别占位，保留所有字段。
3. 验证WAITING、LIVE、DISCONNECTED、恢复、乱序、降级、开发回放以及长ID和长错误文本；各状态截图在1600×900及1280×720均无遮挡、裁切。
4. 重建并重开候选toe/tox，运行现有专项测试、权限检查、节点错误检查；以新证据提交复核。

本轮TD自动化接口127.0.0.1:9981返回ECONNREFUSED；未生成新运行制品或运行验收证据。新版图片不替代原T-01测试证据，不更改任务注册表状态。

## 生成方式

使用内置image_gen工具，提示词见`workbench-v2-prompt.txt`。最终预览为`workbench-v2.png`。
