# D01 当前真实采集交接

当前任务WAIT_DEP_EXTERNAL，P-02前置已完成，但真实设备、目标机兼容、实际驱动与30分钟证据未落实；岗位P-HARDWARE尚无真实领取人。当前规范化不是任务签收，也不新增第三方SDK依赖。

## 通道与来源订正

Polar官方H10说明支持HR/RR及130Hz ECG；官方SDK主要面向Android/iOS，不把其版本号当Windows Python驱动兼容证明。当前Windows路径仍须由D-01验证Bleak、蓝牙适配器、固件和实际发现的服务。[官方SDK说明](https://github.com/polarofficial/polar-ble-sdk/blob/master/README.md)、[H10能力](https://github.com/polarofficial/polar-ble-sdk/blob/master/documentation/products/PolarH10.md)。

ECG使用PMD服务及控制/数据特征；HR/RR是另一通道，不能将HR特征当原始ECG。官方TYPE_0解码每样本3字节有符号微伏，不能照旧int16假设写驱动；其他类型需按实际协商支持，不按猜测解码。[PMD源码](https://raw.githubusercontent.com/polarofficial/polar-ble-sdk/master/sources/Android/android-communications/library/src/main/java/com/polar/androidcommunications/api/ble/model/gatt/client/pmd/BlePMDClient.kt)、[ECG源码](https://raw.githubusercontent.com/polarofficial/polar-ble-sdk/master/sources/Android/android-communications/library/src/main/java/com/polar/androidcommunications/api/ble/model/gatt/client/pmd/model/EcgData.kt)。

呼吸主通道属于D-02真实呼吸带；H10派生EDR不能冒充该输入。HRV是后续对真实ECG/RR计算的结果，不是假定设备直接通知的原始HRV流。旧10Hz帧、CSV与模拟天气字段只是开发历史，当前对外遥测由P-01/F-01/F-05统一发布。

## 原始记录与时钟

每个通知在主机接收时取得单调时间并保留原始字节、逻辑来源、来源策略、每来源递增packet_seq、设备时间、时钟域和样本数，使用P-02既有RawPacket/append_raw_packet，不新增归档格式。ECG/RR通知不能先降采样后才记录原件；S-01同步、S-02交互状态估计与A-01离线分析消费原始事实及派生结果。

P-02接受的H10来源固定为polar_h10_ecg/polar_h10_rr，正式source_policy=real。已有通知且设备时间未知时，device_time_ns=null、payload仍保留字节、missing_reason_code保持null；时钟缺失原因另写L1时钟/状态记录。missing_reason_code只用于payload=null、sample_count=0的缺包记录，不能为了设备时间未知而让合法通知被存储拒绝。

设备时间与主机时间分别记录；缺设备时间使用null并说明来源缺失，不填零、不以接收时间伪装设备时间。官方说明H10重启后时间会重置，HR等通道不一定有可定义的设备样本时刻；时钟域及跨重连映射交S-01，不直接认作同步UTC。[官方时间说明](https://github.com/polarofficial/polar-ble-sdk/blob/master/documentation/TimeSystemExplained.md)。

## 真机验收和责任

AC1需目标Windows机器真实连续1800秒原始记录与报告；AC2说明ECG/RR通知包数、样本数、序号与缺失、设备/主机时间语义；AC3真实断流重连、停止清理、缺失状态和无正式Mock回退。设备序列号、MAC等受限身份按G-02在仓库外配置，仓库只用逻辑source_id。P-02合成压力、通用DeviceManager测试不能证明这些验收。

P-HARDWARE领取人负责设备与适配；S-01负责时间与SQI，P-02负责追加记录，I-01负责双真机800秒全链，G-05负责相应活动准入。先确认设备和官方协议再转READY/领取；没有这些证据不伪造DONE。当前未实现适配器是待交付，不将本轮治理检查作为真机PASS。
