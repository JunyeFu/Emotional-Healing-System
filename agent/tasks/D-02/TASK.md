# D-02 真实呼吸与运动采集

## 当前状态与责任

注册表权威状态为WAIT_DEP_EXTERNAL，前置P-02已DONE，岗位P-HARDWARE，尚无实际领取人、执行分支或第二人签署。规范化不等于设备任务完成。

## 目标与交付

接入PLUX respiBAN BLE，提供DeviceSource适配器、400Hz呼吸与运动原始记录、配置和连接状态事件。AC1真机连续30分钟；AC2通道、采样率、序号与时间戳可复核；AC3断流重连且正式模式不回退Mock。序列号、设备地址和真实采集原件留在受限仓库外。

当前实现与证据边界见[采集交接](outputs/current-acquisition.md)。执行验证入口为`execution/verify.ps1`，证据写入`evidence/`；不得把合成测试写成真机验收。

## 四天执行过程

1. 取得指定型号的厂商SDK/协议及许可，完成Windows目标机兼容前测；记录固件、SDK、架构与设备身份，不套用通用Hub示例。
2. 实现连接和采集；原始通知先交P-02，原生样本批次交S-01。确认7通道布局、时间与序号语义，不猜UUID或字节格式。
3. 完成断连重连、缺包与重置取证；真实模式保持缺失和降级，不填零、EDR或Mock。
4. 完成独立30分钟稳定采集及与H10双设备前测，交付采样率/丢包/时钟报告，再申请独立复核及真实第二人签收。

## 技能与上下游

需要BLE、SDK接入、批包采集、时间戳和Python测试。国内资料沿用L-BLE与L-PY：[Seeed中文BLE入门](https://wiki.seeedstudio.com/cn/XIAO_ESP32C3_Bluetooth_Usage/)、[Python中文教程](https://docs.python.org/zh-cn/3/tutorial/)。正式字节接口必须以厂商协议为准。

P-02保存原始通知，D-01提供ECG/RR，S-01同步与SQI，S-02交互状态估计，I-01双真机全链。领取时通过现有治理流程冻结输入；UP-06/M06保持开放。
