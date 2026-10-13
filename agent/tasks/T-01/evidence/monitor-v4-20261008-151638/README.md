# TD monitor-v4 原生运行证据

候选：[打开TD工程](T01_Workbench_A.monitor-v4.candidate.toe)。
TouchDesigner 2025.32820；原始工程保留。候选仍在隔离目录运行，模拟发送器已结束。

85项T-01/F-04及验证器主机测试通过；12项TD原生截图检查通过。
六类曲线真实点击切换；三轴RGB、RR紫色使用实际TOP像素核查。
修复了首次运行中Script TOP缓存旧回调导致“标签切换而曲线未切换”的问题。

- 01-waiting：启动等待；01-device-only：无会话遥测仍可查看设备预览。
- 02-devices-live：呼吸/ECG；03-motion-rr：三轴加速度/RR；04-gyro-hr：三轴角速度/心率。
- 05-clicked：已点击、待Python确认；06-recording：模拟会话录制；09-completed：完成。
- 07-large、08-large：1600×900、1920×1080布局；实际PNG受当前环境限制均为1280×720，未放大冒充原生高分辨率。
- 10-details：链路页真实点击；11-final：完成后计数保持。

模拟会话保存一个JSONL，共347条；录制前0条，结束后追加0条。
development-recordings内全部是本轮合成fixture，不含参与者真实数据。
记录末行completed，所有数据属于同一session_id且接收时间位于开始/结束边界内。
HR/RR模拟输入恒定，趋势呈水平线是正确表现。

复核命令：
`py -3.14 agent/tasks/T-01/execution/verify_monitor_capture.py agent/tasks/T-01/evidence/monitor-v4-20261008-151638`

这不是真实Unity点击、真实设备或正式P-02链验收。真实事件/存储桥待接线。
