# T-01 六类曲线与录制前检查

本轮将已选中的上下双波形、右侧会话信息布局落到TD原生界面。
不修改任务状态，不覆盖历史签收工程。

## 显示

呼吸 #2563A6；ECG和心率 #237A47；RR间期 #7850A0。
加速度和角速度各三轴：X #B63B3B、Y #237A47、Z #2563A6。
运动通道使用X/Y/Z文字与颜色共同标识，不把三轴压成一条曲线。
原始ECG窗口6秒，其他视图30秒；切换只改变本设备图表。
无数据保留空图并标明未接入，不生成替代波形。

会话时长为分:秒，例如800秒显示13:20；横轴同样为分:秒。
样本龄小于一分钟显示秒（如0.02秒），超过一分钟显示分:秒。
RR间期保留ms，ECG保留μV，心率保留bpm；这几项不是会话时长。

## 录制与Unity接口

当前实现的是开发数据录制，不是屏幕录像，也不替代P-02正式存储。
启动默认显示“正在等待Unity开始 · 预览不计入录制”。
六类曲线、设备状态与明细始终可查看，等待期间没有录制文件。
一次实验以一个匿名session_id为边界，开始后不按天气拆文件；完成或中止后停止追加。
参与者身份与session_id的对应仍由现有上游分配系统负责，不在TD录入姓名或联系方式。

预留接口使用已有本机UDP5005，消息名session_observation，version=1.0。
这不是F-01控制消息，不允许TD借此发出控制命令。
开发消息字段：event_id、session_id、source_mode=dev_mock、event。
event可为unity_start_clicked、started、completed、aborted。
Unity点击只能显示等待确认；started还要求authority=python_session_core和unity_start_confirmed=true。
当前模拟验证器发送这些字段以验证UI，不构成经过认证的真实上游回执。
正式接线需由Python消费Unity请求/确认，完成P-02存储后发布只读状态；
真实模式当前明确返回FORMAL_RECORDING_REQUIRES_P02_BRIDGE，不能使用开发文件冒充正式记录。

开发记录位于候选工程同级development-recordings，每会话独立JSONL。
记录开始/结束、有效遥测、设备预览批次与TD接收时间；等待数据不回填。
逐次写入并同步磁盘；写入失败停止记录、显示错误。进程意外退出的文件保留，
无completed/aborted末行表示未完整关闭，不能按完整实验使用。
此文件只包含TD收到的开发数据；正式设备原始流仍应从D-01/D-02进入P-02。

## 运动曲线输入

device_preview v1.0增加可选acceleration和angular_velocity对象，均为x/y/z数组，
数组长度与samples一致，沿用该批时间戳和采样率。
必须同时指定acceleration_unit=m/s2或angular_velocity_unit=rad/s。
设备原生计数、g或deg/s须在上游按真实SDK标定后转换，不在TD猜测单位。
HR与RR趋势使用已有hr_bpm和rr_ms字段；趋势样点不冒充逐心搏原始事件。

## 运行

生成与原生测试：py -3.14 agent/tasks/T-01/execution/capture_workbench.py --monitor
核对：py -3.14 agent/tasks/T-01/execution/verify_monitor_capture.py <证据目录>
测试用独立候选副本，并保留原工程。模拟流结束后页面显示历史波形。
重新打开候选默认回到等待状态，不自动继续旧录制。

## 色彩依据

LabChart允许自定义信号颜色：https://www.adinstruments.com/support/labchart-lightning
ROS坐标X红Y绿Z蓝：https://docs.ros.org/indigo/api/rviz/html/c%2B%2B/classrviz_1_1Axes.html
ECG绿色实例：https://images.philips.com/is/content/PhilipsConsumer/Campaigns/CA08092022_nbp/Mx400_ifu_eng.pdf
具体十六进制数值为项目白底配色，不宣称六类数据存在统一行业标准。
