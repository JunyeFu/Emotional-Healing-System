# 单窗口连续实验工作台

## 页面与操作

同一个WorkbenchA根面板按状态显示主页面、准备、等待、监控或收尾。
本轮实验记录和设备明细是同窗口只读视图；返回时回到当前阶段，不重置流程。

- 主页面：新建实验准备、本轮实验记录、完成/中止/待收尾统计。
- 准备：新会话编号，匿名参与者和条件只读；六类曲线保持可用。前测、Unity、记录准备均等待回执。
- 等待：提交准备须Python确认。Unity点击只改变提示；Python确认started后才创建实验记录。
- 监控：暂停/恢复/中止按钮只发请求，回执才改变会话状态。有效用时与总历时分开，暂停冻结有效时间但保留连续数据。
- 收尾：正常完成或中止分别展示，记录封存和后测分别确认。未齐时下一场和返回主页面不可用。
- 完成收尾并准备下一次：生成新会话，清空前场曲线、计时、分配和实验状态；UDP接收及窗口不重启。

I/G/X分别消费独立显示字段。现有v2.2目标字段不自动当作I或G，新接口未到时显示未接入。
曲线颜色、单位和窗口沿用monitor-v4；ECG为6秒，其他为30秒；RR保持ms。

## 当前接线范围

本轮交付TD原生页面和开发工作流，所有控制确认使用模拟桥；不修改正式F-01协议。
真实Unity请求、正式SessionCore、P-02、问卷服务和活动准入桥尚未接入本界面。
主页面及每场页持续显示模拟模式。真实source_mode消息被拒绝，不自动改成模拟数据运行。

工作流模块：agent/modules/03-TouchDesigner/t01_telemetry_panel/experiment_workflow.py。
原生构建器：agent/tasks/T-01/execution/build_workbench_flow.py。

开发数据放在当前TOE所在目录的development-workflow：

- workflow.json：会话索引和收尾状态；原子替换保存，索引路径为相对路径。
- operator-requests.jsonl：开发请求出口，含request_id、session_id、action、requested_ns。
- recordings/*.jsonl：每场独立数据文件，开始前不创建，结束后不再追加；中止保存部分记录。

准备期可能写工作流请求元数据，但不写入实验数据文件。一次实验文件覆盖全部天气与暂停，不按天气分割。
重启后可读历史。未正常关闭的运行标为INTERRUPTED，不恢复体验、不标为封存完成。
参与者是否可再次参加由既有去重/分配系统负责；新建本地会话不是再次参加的资格。

## 开发消息

沿用本机UDP5005的session_observation、version=1.0。新增字段和事件均是开发接口，非正式协议冻结。
每条需要event_id、session_id、source_mode=dev_mock、authority=python_session_core。
事件须匹配当前session_id；重复事件不重复执行。

| 事件 | 主要字段与作用 |
|---|---|
| preparation_status | participant、condition=A/B、pretest、unity_ready、store_ready；后三项为布尔回执状态 |
| prepared | 对应prepare请求的request_id；进入等待 |
| cancelled | 对应cancel_prepare请求；尚未开始时返回主页 |
| unity_start_clicked | 仅显示Unity点击，尚不录制 |
| started | unity_start_confirmed=true；在等待阶段创建本场开发记录 |
| paused / resumed | 匹配pause/resume请求的request_id；更新有效时钟 |
| completed / aborted | 结束并关闭本场文件，进入收尾 |
| closeout_status | sealed、posttest布尔回执；缺失或false时禁止下一场 |
| request_rejected | 匹配request_id；显示拒绝并释放该请求状态 |
| guidance_status | ideal、guide、actual各为吸气/呼气/保持/未接入；三个来源独立 |

本机开发桥以JSONL作为请求出口。正式接入时应由T-02/会话编排对应实现消费请求并回复，不能把字段中的authority字符串当作身份认证。
设备预览不改变实验状态；只接受当前会话数据进入该会话记录。历史列表不触发重新暴露、控制发送或数据重写。

## 验证

主机测试覆盖三场连续记录、回执缺失/错会话/错请求、暂停计时、取消、封存失败、只读历史、重开后中断标记。
原生测试通过真实面板点击依次完成两次正常、一场中止、下一次准备和历史查看；各阶段始终仅一个内容页面可见。
执行：py -3.14 agent/tasks/T-01/execution/capture_workbench.py --flow。
核对：py -3.14 agent/tasks/T-01/execution/verify_flow_capture.py <本轮证据目录>。
不能把开发桥验证写成真实设备、真实Unity、正式准入或LIVE_E2E完成。
