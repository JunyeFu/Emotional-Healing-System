# D02 真实呼吸采集与交接

## 当前结论

D-02仍WAIT_DEP_EXTERNAL，岗位P-HARDWARE，尚未领取。仓库没有respiBAN真机驱动、厂商SDK回执或30分钟记录；本轮完成规范化及共享呼吸批次修复，不申请DONE。

## 已核验规格与待取得接口

设备为PLUX respiBAN BLE，不是通用Hub加任意呼吸传感器。其呼吸1通道28-bit、加速度3通道16-bit、角速度3通道16-bit，规格采样率400Hz。呼吸量是感应带相关值，不直接等于绝对呼吸体积。[官方数据表第4-7页和第9-10页](https://support.pluxbiosignals.com/wp-content/uploads/2024/05/respiBAN_BLE_Datasheet.pdf)

厂商专用Wearables API须申请；不能用公开Hub Python示例、旧串口计划或网页宣传推定当前Windows/Python 3.14可用。取得SDK、许可、固件与目标机支持说明后，才能确定UUID、通道次序、端序、序号回绕、时钟和通知批次。当前不猜字节布局。[官方API说明](https://support.pluxbiosignals.com/knowledge-base/official-plux-application-programming-interfaces-apis/)

## 原始记录与在线样本

P-02 `RawPacket`来源固定`plux_respiban`、策略`real`；每通知包保留原始字节、样本数、包序号、设备时间和主机接收单调时间。未知设备时间为null，原因另记L1；有payload时不能设置缺包原因。缺包用payload=null、sample_count=0及原因，禁止填零或合成波形。

若SDK只返回解码数值，不能重新序列化后冒充BLE通知原件。应向厂商取得原始通知接口；无法取得时明确记录接口缺口，按当前P-02原始字节合同先解决再验收。运动轴和原始数值同样需要保留，不只输出幅值。

共享FrameClock现保留`resp_samples`带时间戳批次；`respiration_raw`仍是历史三点均值显示字段，不是400Hz原件。重复tick没有新样本时批次为空，resp有效性为false。该软件改动不证明设备能运行；正式驱动须在降采样前落L0，S-01消费原生通道及时间元数据。

## 验收与下游

连续30分钟相当于标称每通道720000采样时点，验收报告须按实际时长、启用通道、序号及丢包计算，不能只宣称采样率。另留断连/重连、重置后时钟域和双设备持续采集记录。正式路径不回退Mock或H10派生EDR。

D-01给ECG/RR，D-02给真实呼吸和运动，S-01做同步/SQI，S-02做交互状态估计，P-02存原件，I-01做800秒双真机全链。设备型号、佩戴位置、SDK/固件版本随配置交接，受限原件与身份不进仓库。真实责任人领取和UP-06/M06仍开放。
