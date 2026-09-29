# 退役采集方案

位置更新 2026-09-29：下文保留逐包整理时的归档决定与当时进度，旧路径和“待迁移”表述仅解释历史。19项根目录迁移现已落实；当前物理归属见[根目录归属表](../../../root-layout.json)，实际入口以本包TASK及outputs/current文档为准。

旧ble_device.py、设备方案.md和真实设备方案.md已从技术目录实际移入本目录；Git保留原件。旧PolarH10Source的start/read_frame/stop均为NotImplementedError，没有真实驱动或真机验收。

归档原因：旧骨架误把HR/RR特征2A37当ECG，描述int16 ECG和EDR主呼吸通道；旧方案以10Hz/CSV为主且混用多个线程架构，不符合当前D-01/D-02、P-02原始包与F-01/F-05遥测交接。归档保留历史，不直接运行其中Mock包装器，不将其计划当已实现。

DeviceManager、DeviceDriver、RingBuffer、FrameClock和Mock开发模块是跨D/S任务的共享历史实现，暂留技术模块，后续统一迁入agent/modules并修复消费者。没有为本包复制共享代码，也未把24项通用测试解释成真实H10兼容证据。
