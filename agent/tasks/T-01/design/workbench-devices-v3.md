# T-01 双设备工作台

本轮按用户确认暂不使用皮电，仅显示PLUX respiBAN BLE呼吸胸带与Polar H10心电胸带。保留A浅色主题；不改变研究流程、F-01/F-05遥测合同或历史DONE签署范围。

## 页面与字段

总览：接收与输入来源、会话信息、两个等宽设备区、目标/实际呼吸跟随、反馈与降级、TD遥测统计、记录及事件接入情况、固定底栏。设备区独立使用青绿/浅蓝标题带，正文16、标题18；1280×720起布局扩展，不缩放字号。顶部不放项目大标题或未接入的命令按钮。

呼吸区显示连接、近似样本龄、呼吸SQI、30秒相对幅度波形、实际批次采样率和运动通道状态。心电区显示连接、近似样本龄、SQI、6秒ECG波形、HR/RR通道状态、心率bpm、RR间期ms及实际ECG采样率。呼吸纵向按当前窗相对幅度缩放，不能读作绝对气量；ECG显示范围为-1200至1200 μV，不据此判读信号性质。详细值保留原始字段，支持滚动和选择复制。

跟随区不从波形猜步骤：目标/实际周期、步骤、相位、进度直接消费v2.2字段。模块位置从合同0基索引转成1/4至4/4，仅影响文字。恢复值不是情绪结果，锁定与降级分开。记录/事件未接入时明确显示未接入，不生成假事件。设备断连与TD遥测断流分别表达；遥测超时保留灰色末帧历史值，不能凭TD超时改写设备连接事实。

## 只读设备预览消息 v1.0

与遥测共用127.0.0.1 UDP 5005，通过message_type分派；不向Unity发送，不接收操作命令，也不改变正式运行合同。它是设备驱动后续接线的显示接口，不是厂商原始字节协议或正式采集验收。

字段：message_type=device_preview；preview_version=1.0；source_id=plux_respiban或polar_h10_ecg；source_mode=dev_mock或real；session_id；clock_domain_id；递增packet_seq；last_sample_monotonic_ns；sent_monotonic_ns；sample_rate_hz；unit=relative或uV；samples（最多400个，缺失样本为null）；device_state。可选motion_state、rr_state采用LIVE/DISCONNECTED/UNKNOWN；可选hr_bpm和rr_ms缺失时不补零。

两个时间戳必须同属发送端时钟域。样本等间隔，末样本时间与采样率重建批内时间轴；不直接相减发送端与TD的绝对读数。近似样本龄=发送时样本龄+TD接收后的经过时间，**不包含未知传输延迟，不是设备到屏幕延迟**；因此总览标注“样本龄≈”。两秒没有新可用数据时冻结并标历史。会话或来源时钟身份变化清空对应缓存；会话不匹配的波形不显示。

呼吸保留30秒、ECG保留6秒，按真实批次点绘图；逐像素保留幅度极值，避免400Hz重复绘制开销。缺失点与≥500ms时间缺口断开，不补零或平滑连接。模拟源只生成呼吸/ECG与示意HR/RR，没有发送运动分轴，运动状态保持未知。实际运动分轴仍待D-02接入。

外部消息拒收错误值、非法单位、版本、非有限样本、重复/倒序或重叠批次；坏消息不推进原遥测计数。原遥测非法SQI另行拒收，不修改共享Schema。

## 使用与验证

- `execution/capture_workbench.py --devices`：隔离副本构建、模拟UDP、14种原生捕获。源TOE不覆盖。
- `execution/verify_device_capture.py <证据目录>`：核查正常收流、拒收注入、缓存、实际曲线像素、断流、降级、点击与滚动。
- `execution/simulate_device_preview.py`：明确标记dev_mock的批次生成器，400Hz呼吸与130HzECG；界面刷新仍≤20Hz。
- `build_workbench_devices.py`：新候选生成器；设备接收/绘图代码内置DAT。历史构建器仅增加“不在中间保存”参数供新构建器复用。

曲线采用[TD Script TOP官方API](https://docs.derivative.ca/ScriptTOP_Class)的onCook/copyNumpyArray；所有截图来自TD原生TOP。非商业版实际导出分辨率须按回执记录，较大布局截图不称为较大像素截图。候选保留禁用的取证回调，不自动发送fixture；真实设备、SDK与T-02仍各自验收。
