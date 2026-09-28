# 数据采集模块

当前任务入口：[D-01真实ECG与RR交接](../../agent/tasks/D-01/outputs/current-acquisition.md)。D-01仍WAIT_DEP_EXTERNAL、未领取；D-02负责独立真实呼吸带，S-01负责同步与SQI，P-02负责原始字节追加记录。

DeviceDriver/DeviceManager/RingBuffer/FrameClock为共享历史实现，24项通用测试不能证明真机适配。mock_data.py只用于明确开发fixture，不用于正式采集或替代缺失数据。

旧BLE骨架及两份方案已迁入[历史归档](../../agent/tasks/D-01/archive/README.md)，不再按其中HR特征采ECG、EDR主呼吸、10Hz或CSV正式记录假设实施。正式原始流、会话控制和20Hz遥测按P-02/P-01/F-01/F-05交接。
