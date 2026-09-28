# 数据采集模块

当前任务入口：[D-01真实ECG与RR交接](../../agent/tasks/D-01/outputs/current-acquisition.md)与[D-02真实呼吸与运动交接](../../agent/tasks/D-02/outputs/current-acquisition.md)。两包仍WAIT_DEP_EXTERNAL、未领取；S-01负责同步与SQI，P-02负责原始字节追加记录。

DeviceDriver/DeviceManager/RingBuffer/FrameClock为共享历史实现，28项通用测试不能证明真机适配。FrameClock保留ECG与呼吸原生批次，呼吸均值仅作历史显示；没有新呼吸样本时有效性为false。DeviceManager连接后质量保持unknown，不能据连接成功声称GOOD。mock_data.py只用于明确开发fixture，不用于正式采集或替代缺失数据。

同步与SQI当前入口为[S-01交接](../../agent/tasks/S-01/outputs/current-quality.md)，真实时钟映射、算法、阈值和双真机报告仍未完成。

旧BLE骨架及两份方案已迁入[历史归档](../../agent/tasks/D-01/archive/README.md)，不再按其中HR特征采ECG、EDR主呼吸、10Hz或CSV正式记录假设实施。正式原始流、会话控制和20Hz遥测按P-02/P-01/F-01/F-05交接。
