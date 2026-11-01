# 心率设备需求、蓝牙接入与采购清单

核查日期：2026-10-18。范围：用户提供的22条天猫截图、当前SRP采集/会话/记录接口和厂方公开资料；不是采购批准或真机验收。价格均为截图展示价，不是本次核实的到手价。合并三组明显重复条目后共19项，未把相似外观当作型号证明。

## 1. 重新确认需求

当前依据为[D-01](../tasks/D-01/outputs/current-acquisition.md)、[D-02](../tasks/D-02/outputs/current-acquisition.md)、[采集模块](../modules/acquisition/README.md)、[SessionCore](../modules/srp_session_core/README.md)及[SessionStore](../modules/srp_session_store/README.md)。

| 数据/能力 | 当前用途与选择要求 |
|---|---|
| 实时HR，单位bpm | 操作台心率显示、通道状态与辅助评估；只有HR不足以替代D-01 |
| 原生RR逐搏间期 | HRV与逐搏分析的输入；不能用60000/显示心率伪造RR序列 |
| 原始ECG波形 | D-01 AC1明确保留ECG/RR原始证据；要能向自己的程序导出，不是商品页写“ECG测心率”即可 |
| 时钟、有效性、断流信息 | 设备时钟与主机接收单调时间分开，保留原始通知包和原生批次，连接成功不等于质量合格 |
| 独立呼吸测量 | 仍由D-02承担，不能拿HR、RR或推算呼吸代替独立实际呼吸X |

H10定位为辅助测量，不自动推断情绪或进入快速控制；A组本人数据只进入评估，不改变参与者输出。设备功能也不能替代PANAS等结果测量。

如果为了预算只保留HR/RR而放弃ECG，部分便宜胸带可能够用，但这属于修改D-01采集范围，必须先明确新的研究分析目标，不能把“便宜心率显示器”写成当前任务的等价替代。光学臂带测得的脉搏间期也不能无说明地当作ECG来源RR。

## 2. 蓝牙协议到底是什么

### 标准心率数据

- 优先使用BLE GATT Heart Rate Service，服务UUID为`0x180D`，通知特征为`0x2A37`，不是蓝牙串口SPP或直接发送JSON。
- 通知是二进制：`Flags + HR值 + 可选能量字段 + 可选RR数组`。Flags决定HR是8位还是16位、是否含RR；多字节数值按小端解析。
- 标准RR原始单位为`1/1024秒`，换为毫秒时乘`1000/1024`；Polar SDK返回的RR已是毫秒，不能再换一次。
- RR是可选字段，BLE标志、胸带形态及“支持HRV”字样均不能证明某个固件通过`0x2A37`持续开放原生RR。每个准确SKU都需查GATT和实际通知。
- ANT+是另一套无线协议，普通电脑蓝牙不能接收ANT+；本项目优先BLE，不为已支持BLE的设备额外购买ANT+接收器。

依据：[Bluetooth SIG心率服务](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/HRS_v1.0/out/en/index-en.html)、[SIG UUID分配表](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Assigned_Numbers/out/en/index-en.html)、[SIG数据转码说明](https://www.bluetooth.com/wp-content/uploads/2019/03/PHD_Transcoding_WP_v16.pdf)、[Polar RR单位说明](https://github.com/polarofficial/polar-ble-sdk/issues/343)。

### H10原始ECG

[Polar H10官方能力表](https://raw.githubusercontent.com/polarofficial/polar-ble-sdk/master/documentation/products/PolarH10.md)明确支持HR/RR及130Hz、微伏单位的原始ECG。ECG走厂商PMD服务，不走`0x2A37`：

| 项目 | UUID |
|---|---|
| PMD服务 | `FB005C80-02E7-F387-1CAD-8ACD2D8DF0C8` |
| 控制点 | `FB005C81-02E7-F387-1CAD-8ACD2D8DF0C8` |
| 数据通知 | `FB005C82-02E7-F387-1CAD-8ACD2D8DF0C8` |

按官方格式查询能力、配置并启动ECG通知，解析设备时间及批次；不能将HR通知当成ECG样本。[PMD官方实现](https://raw.githubusercontent.com/polarofficial/polar-ble-sdk/master/sources/Android/android-communications/library/src/main/java/com/polar/androidcommunications/api/ble/model/gatt/client/pmd/BlePMDClient.kt)。

[Polar H9官方能力表](https://raw.githubusercontent.com/polarofficial/polar-ble-sdk/master/documentation/products/PolarH9.md)只有HR/RR，并明确不支持H10那样的PMD流；不能因为同是Polar胸带就替换。

## 3. 怎么连接本项目各个监控

建议由一个Python采集进程连接传感器，再分发给项目各端，不让TD、Unity和手机App分别争抢蓝牙连接。

1. Windows BLE适配器 -> Python采集驱动：标准HR/RR订阅HRS；H10 ECG另订阅PMD。Windows可用[Bleak WinRT后端](https://bleak.readthedocs.io/en/latest/backends/windows.html)，但项目驱动仍需实现和实机验证。
2. 原始通知包 -> P-02 `SessionArchive.append_raw_packet`：保持原始字节、来源、包序号、设备时间、主机接收单调时间和样本数；不是只保存屏幕上的HR或CSV曲线。
3. 解码后的ECG/RR与独立呼吸批次 -> S-01同步/SQI -> S-02等计算所需特征 -> SessionCore。HRV按有效逐搏序列计算，不是每帧凭HR生成。
4. 同一完整遥测帧按现有合同镜像到TD的UDP `5005`和Unity的UDP `5006`，最多20Hz。TD用于操作员观察；Unity按批准的条件和G渲染，不把所有辅助数据自动变成参与者反馈。
5. TCP `5010`是现有会话控制/ACK/渲染回执通道，不是胸带蓝牙端口。以上端口为既有合同说明，本次没有启动或占用。

20Hz是遥测发布上限，不是ECG采样率；130Hz ECG必须保留原生样本，不能为匹配界面刷新而丢成20Hz原始数据。

[Polar官方SDK](https://github.com/polarofficial/polar-ble-sdk)面向Android/iOS，不是现成的官方Windows Python包。主选Windows/Bleak按公开协议实现；使用Android官方SDK再桥接电脑是另一条可行路线，但要增加手机端开发和时钟同步工作，不视为现成接入。

### 当前实现缺口

- 当前采集目录提供抽象`DeviceDriver`、管理、缓冲和历史FrameClock，不能据此认定已有可用H10驱动。历史FrameClock的10Hz协调也不是当前正式20Hz遥测实现。
- D-01证据中的`real_device_acceptance`仍为`NOT_RUN`，当前TD手动mock验收不证明真实胸带或呼吸设备可用。
- D-02输入仍记载respiBAN专用SDK未收到、GATT未核定；它不通过标准心率HRS接入，双设备并行仍需联调。
- 本次主机执行`py -3.14`提示无匹配运行时；没有安装或改动解释器。正式接入前须确认当前解释器、Bleak及蓝牙驱动组合，不能沿用旧环境表即声称可运行。

## 4. 截图清单：按价格升序

“HR候选”表示厂方文档支持蓝牙心率接入方向，仍需编写项目驱动并实测；不是已在SRP通过。除明确说明外，“未确证”指本次未查到开放数据接口的证据，不等于断言硬件绝对没有该能力。

| 截图价/元 | 截图条目 | 蓝牙/无线核查 | RR与原始ECG判断 | 当前选择 |
|---:|---|---|---|---|
| 39 | #22 ROMARVEL X2 | 标题ROMARVEL但图片为XOSS，准确厂家/SKU不明 | 均未确证 | 暂不买，不能套用XOSS官方规格 |
| 89 | #6 行者心率带，图示XOSS X2 | 若为正品X2，厂方列BLE+ANT+ | RR未确证；未见开放ECG | 低价HR联调候选，先确认型号和整机 |
| 89 | #16 CYCPLUS H2胸带 | 厂方H2手册列BLE+ANT+；当前手册入口标题H2 Pro，须核实代际 | RR未确证；未见开放ECG | 低价HR联调候选，不能直接替代D-01 |
| 99 | #5 迈金胸带，未写型号 | H303等厂方型号支持BLE+ANT+，本链接型号未定 | 本SKU的RR/ECG未确证 | 先索取准确型号，不默认H303/H64 |
| 159 | #15 CYCPLUS H1 | 厂方确认是臂带，BLE+ANT+ | 非原始ECG胸带；原生间期输出未确证 | 仅HR演示候选 |
| 180 | #8 XOSS光学臂带，型号未写明 | 厂方臂带系列支持BLE+ANT+，需核实具体型号 | RR/PPI开放未确证；不提供ECG依据 | 仅HR演示候选 |
| 189 | #7 iGPSPORT HR50胸带 | 官方规格ECG传感原理、BLE+ANT+ | “ECG传感器”不证明能导出波形；RR未确证 | HR联调候选 |
| 199 | #3/#14 COOSPO光学臂带，疑似HW9 | 若为HW9，厂方列BLE+ANT+ | 间期未确证；不作为ECG来源 | 型号确认后仅HR候选 |
| 199 | #17 COOSPO H9Z胸带 | 官方BLE+ANT+、第三方App兼容 | RR未获厂方接口确证；未见开放ECG | HR联调候选，不写成HRV已支持 |
| 199 | #19 黑鸟HR5臂带 | 官方列Bluetooth+ANT+ | 原生间期未确证；不作为ECG来源 | 仅HR候选 |
| 200 | #4 iGPSPORT，标题写码表、图片为臂带 | 标题/图片不一致，未确定型号 | 均未确证 | 先核SKU，不擅自归为HR70或HR80 |
| 269 | #10 迈金H613胸带 | 官方标准BLE+ANT+，支持多路BLE | 原生RR未确证；未见开放ECG | HR候选，本项目不必为多路BLE加价 |
| 289 | #9 迈金H803光学臂带 | 官方标准BLE+ANT+ | 原生间期未确证；不作为ECG来源 | 仅HR候选 |
| 399 | #2 iGPSPORT HR80光学臂带 | 官方PPG、BLE+ANT+、双BLE | 原生间期未确证；不作为ECG来源 | 仅HR候选，当前需求无须优先 |
| 499 | #21 光粒HandPlus B2 | 厂方支持Bluetooth+ANT+和第三方设备 | 未见开放RR/ECG接口确证 | 游泳用途非本项目优先 |
| 599 | #12/#20 COROS高驰臂带 | 官方仅BLE，无ANT+，可连3台BLE设备 | 未见本臂带开放RR/ECG确证 | HR可评估，按当前需求不优先 |
| 630起 | #13 佳明HRM600/200混合链接 | 确定型号后均可核对BLE/ANT+；第三方设备注意Open模式 | 厂方支持HR/HRV；Windows原生RR须实测，未见开放ECG | 不能把630元当作HRM600整机报价 |
| 889 | #18 Polar胸带，未显示H9/H10 | 两者都有BLE心率，但功能不相同 | H9有HR/RR无PMD；H10另有130Hz ECG | 只有确认整机为H10才符合当前能力要求 |
| 1280 | #1/#11 佳明HRM600 | 官方BLE+ANT+，第三方接入注意Open模式 | 厂方支持HR/HRV；未见开放原始ECG依据 | 不因价格高就判为比H10更适配 |

### 厂方核查来源

- [XOSS X2产品](https://xoss.co/fr/products/xoss-chest-strap-heart-rate-monitor-bluetooth-ant)、[XOSS胸带与臂带支持](https://support.xoss.co/hc/support/en/categories/xoss-chest-strap-heart-rate-monitor-armband)。不能据X2 Pro或BBP资料替未定型号背书。
- [CYCPLUS官方手册入口](https://www.cycplus.com/ja/pages/instruction-manuals)、[H2手册](https://cdn.shopify.com/s/files/1/0413/9597/8398/files/BZ-4141010192-04_H2.pdf?v=1755507910)、[H1手册](https://cdn.shopify.com/s/files/1/0413/9597/8398/files/BZ-4141010093-03_H1.pdf?v=1755507906)、[H1臂带产品](https://www.cycplus.com/products/cycplus-h1-heart-rate-monitor-band)。已放大检查H2/H1厂方手册中的BLE/ANT+参数。
- [迈金H303手册](https://blog.magene.com/wp-content/uploads/2023/02/H303-Manual.pdf)、[H613规格](https://fr.magene.com/fr/sensors/232-moniteur-de-frequence-cardiaque-h613.html)、[迈金官方产品目录，含H803](https://b2b.magene.com/wp-content/uploads/2025/08/All-Magene-products.pdf)。
- [iGPSPORT HR50](https://www.igpsport.com/product/hr50)、[HR80](https://www.igpsport.com/product/hr80)。
- [COOSPO H9Z](https://www.coospo.com/products/h9z-chest-heart-rate-monitor?from_collection=heart-rate-monitor)、[H9Z连接排障](https://www.coospo.com/a/faq/article/57801)、[HW9厂方产品](https://www.coospo.com/pt/products/hw9-bracadeira-monitor-de-frequencia-cardiaca?from_collection=monitor-de-frequencia-cardiaca)。H9Z排障提示不要同时连接两个App，统一采集再分发可避免此类占用。
- [黑鸟官方HR5介绍](https://blackbirdsport.com/en)、[光粒B2配对与第三方设备说明](https://holosport.zendesk.com/hc/en-us/articles/53966897843091-How-do-I-pair-HandPlus-B2-with-the-HoloSport-App-or-smart-swim-goggles)、[COROS臂带FAQ](https://support.coros.com/hc/en-us/articles/17458038294292-COROS-Heart-Rate-Monitor-FAQs)。
- [Garmin HRM200](https://www.garmin.com.sg/products/wearables/hrm-200-s/)、[HRM600](https://www.garmin.com.sg/products/intosports/hrm-600-s/)、[HRM600 Open/Secure连接说明](https://www8.garmin.com/manuals-apac/webhelp/hrm600/EN-SG/GUID-8D1D35CF-B3F7-4A3C-A796-4E8A3160C396-9403.html)。

## 5. 最终建议与到货清单

**按现有D-01范围：首选准确型号的Polar H10整机加胸带。** 本次核对的型号中，H10有最明确的HR/RR和原始ECG公开接口依据；Windows驱动与双设备全链仍未完成。截图889元只有核实是H10整机后才可作为其预算，当前不声称它是H10的已核到手价，也不声称已证明全市场最低价。

**只做便宜HR联调：先比较89元XOSS X2和89元CYCPLUS H2。** 正品、整机、对应型号和退换条件确认后，先购一套验证，不批量采购。不为本项目的单机统一采集优先支付多BLE连接、跑步动态、游泳或品牌溢价；这些设备不替代正式ECG/RR任务。

购买前要求卖家确认：准确型号/代际、整机含传感器和胸带、BLE标准HR服务、能否向自写程序输出原生RR、原始ECG的SDK/协议文档。不能只回复“可连App”“测心电”“支持HRV”。

到货按以下最小顺序验证，全部尚未执行：

1. 穿戴唤醒，Python扫描并枚举GATT，核对准确设备而非手机App占用；记录固件和硬件型号。
2. 订阅HR通知，保存实际二进制包，确认HR字段与RR存在位，检查原生RR而非HR倒数；缺失保留缺失。
3. H10另启动PMD，确认真实130Hz ECG、单位、原生样本批次和设备时钟，验证HR/RR与ECG并行。
4. 与D-02同时采集，核对S-01时间/SQI；P-02能写入并读回两路原始包；TD/Unity观察同会话遥测，原始ECG不被界面刷新降采样。
5. 持续覆盖一次完整计划会话，并检查佩戴接触不良、摘下、断连和重连。显示缺失/未知，不自动切回mock；采集接入不自动开始实验，仍由操作员按现有准备和开始流程执行。

结论边界：官方协议可行性已核；任何商品的本项目真机验收均未通过本次工作获得。采购选择与驱动实现、设备验收、正式实验准入分别处理。
