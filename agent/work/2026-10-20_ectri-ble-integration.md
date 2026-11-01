# ECTRI APK 蓝牙流程分析与 BigRun 接入

## 结论

**未发现 BigRun 对应 ManDevice 路径存在私钥认证或必须安装手机 App 才能连接的步骤。不能据现有 GATT 错误认定设备主动拒绝了电脑。** APK 的关键行为是 LE 连接、服务发现、通知订阅、串行命令初始化。已将可确认的行为独立实现到现有 BigRun 驱动，不复制整个 App。

此前真实测试曾收到 ECG/ACC/HR/RR，约 47 秒后断连；这否定了“完全不能接收”，但没有定位断连原因。佩戴接触、单客户端占用、Windows 链路、服务缓存和模式切换需分开判断。本轮只做静态分析与软件测试，未扫描蓝牙、连接设备或操作 TD/Unity。

## 输入与核查位置

- 用户 APK：`D:/Wecheat/xwechat_files/wxid_xhivgw8tj7kt22_8232/msg/file/2026-10/base.apk(2).1`，167,924,208 字节，只读提取，不安装或执行。
- 使用 JADX 1.5.6，仅反编译含目标类的 `classes4.dex`；工具及输出在 Git 忽略的 `agent/local/`。该 DEX 共有 2,609 项，工具报告 9 项反编译错误；下列关键方法可读，不宣称整个 APK 已完整分析。
- 证据根目录：`D:/Agent/srp/agent/local/artifacts/ectri-apk-20261020/decompiled/sources/`。下表 Java 路径相对此目录。APK 含手表、戒指等其他协议，不能把它们的密钥/绑定规则套给胸带。未用缓存资产中的版本号代表 APK 安装版本。

| 位置 | 可核查行为 | 本项目处理 |
|---|---|---|
| `com/manridy/manmodel/device/adapter/connect/ManConnectManager.java:273` | `connectGatt` 使用 LE transport，autoConnect=false | 保持单连接；生产入口显式扫描 BLEDevice |
| 同文件 `:332`、`:363` | 请求 MTU 64，MTU回调或超时后发现服务 | 20字节命令适配最小ATT MTU 23，不硬移植 Android MTU/反射缓存接口 |
| 同文件 `:62`、`:89`、`:141` | 设置通知、写CCCD，遍历后发出 `Authenticated` | 等待 Bleak `start_notify` 成功才发送命令；该名称不是密码认证证据 |
| `com/manridy/manmodel/device/adapter/send/ManSendManager.java:172`、`:210` | GATT写回调驱动串行队列 | 所有命令 await、response=True，不并行写 |
| `com/manridy/manmodel/device/adapter/data/ManDeviceData.java:273` | 日期→设备信息→电量→历史读取→ECG设置→模式读取→采集启动 | 只采用实时采集相关部分，省略离线历史及持久设置修改 |
| `com/manridy/manbledevice/bean/ManBean.java:27` | 命令头+参数+零填充至20字节 | 保持已有封包，不加猜测的CRC或AES |
| `com/manridy/manbledevice/bean/write/WriteSportModel.java:11`、`:37` | en=0读取，en=1写入；响应保留en和值 | 写ACK不算读回；显式模式先读、仅写差异、再核对 |
| `com/manridy/manbledevice/bean/write/WriteSportsCommand.java:19`、`:34` | 普通启动参数为 `00 01 00 00 00`；另有GSensor/PPG显式参数 | 保留普通启动，不擅自开启额外标志或PPG |
| `com/manridy/manutils/DateUtils.java:301` | 日期BCD，星期日为0 | 原日期编码一致，增加固定样例测试；日期不当采样时钟 |

私有服务为 `F000EFE0-0451-4000-0000-00000000B000`，写入/通知分别是 `EFE1`、`EFE3`，UUID其他部分相同。

### 不照搬的部分

- `ManDeviceData` 中读休眠/ANT不是关闭休眠/ANT；没有据此发送未经确认的设置写入。
- `startOfflineSportLooper()` 在 `:217` 有既有消息条件，不能据方法名认定启动必带定时保活。`ManSendManager.sendTimeOut()` 在 `:164` 只移除消息；日志中“30秒断开”不证明有活动看门狗。
- 应用其他手表/脚部设备的绑定和密钥不属于这条胸带路径；未复制这些凭据。
- App 的重连及运动恢复行为不能代替 SRP 手动准备/开始门禁，本项目仍断线中止、不自动续接。

## 已落地到基础设施

权威实现：[driver.py](../modules/acquisition/bigrun/driver.py)、[采集CLI](../modules/acquisition/bigrun/__main__.py)、[P-02适配](../modules/acquisition/bigrun/recording.py)。已有 [bigrun.cmd](../runtime/bigrun.cmd) 和 [start-td-bigrun.cmd](../runtime/start-td-bigrun.cmd) 自动消费同一驱动，无第二套采集器。

1. 生产连接显式扫描指定地址并传入 BLEDevice，Windows 强制远端服务发现。参数依据 [Bleak WinRT 文档](https://bleak.readthedocs.io/en/latest/api/args.html#winrt-backend-arguments)；BLEDevice用法依据 [Bleak连接文档](https://bleak.readthedocs.io/en/latest/api/client.html)。无广播只报告扫描阶段缺目标，不叫作拒绝连接，也不提供隐藏的地址猜测回退。
2. 订阅成功后先发 `FC00` 日期、`FC0F05` 信息、`FC0F06` 电量、`FC4206` 速度、`FC4201` 信号、`FC420B00` 采样设置查询。然后读取 `FC0F6000/6200/6100`，最后 `FC14040001` 启动采集；所有命令零填充20字节。
3. `observe` 保持现有模式。显式模式只写差异，要求读回匹配；写ACK、回读缺失、不匹配和断连均不能变成模式验证通过。切换时断线立即退出，不自动重连；不能仅凭时间相邻认定断线就是重启。
4. 状态路径为 `scan → connect_gatt → connected_gatt → subscribe → initialize → read_mode → [configure_mode → verify_mode] → start_acquisition → waiting_for_data → receiving`。仅收到数据包后进入receiving；这仍不是SQI合格或传感器稳定性验收。
5. 控制台、候选JSONL和TD状态包带 `connection_phase`，失败原因及阶段保存到既有P-02 L1 `bigrun_connection`，不另建存储。ECG/RR/HR/ACC原始记录、未知通知、呼吸代理边界、手动实验控制均保持。

## 如何定位下一次失败

| 阶段 | 可以说明什么 | 不可以说明什么 |
|---|---|---|
| scan找不到目标 | 本轮没有发现该地址广播 | 设备拒绝、关机或损坏；此前已出现无广播但WinRT可访问 |
| connect_gatt报错 | 连接/发现服务未完成，保留OS原异常 | 一定缺少App密钥 |
| subscribe报GATT Unreachable | 通知/CCCD尚未成功 | 初始化顺序或采集启动命令已被设备拒绝 |
| configure_mode/verify_mode断线 | 发生于配置窗口；模式重启是候选原因 | 已确认重启或配置成功；仍须重新查询 |
| waiting_for_data | GATT与启动写调用完成，尚待新数据 | 已收到心率/呼吸 |
| receiving后断线 | 至少收过原始数据，需查链路/接触/占用 | 持续性通过，或呼吸代理已校准 |

## 大款胸带到手后复测

佩戴贴合、电极湿润，手机蓝牙/App断开，靠近电脑天线，先不切换模式。运行：

```powershell
Set-Location D:\Agent\srp
agent/runtime/start-td-bigrun.cmd --address C2:22:61:0B:C5:C7 --mode observe --seconds 180
```

这是接入已打开的 BigRun TD 工程的只读预览，不会自动打开桌面或开始实验。若当前地址变化，先用 `agent/runtime/bigrun.cmd scan` 核实。本轮不预填未经核实的输出率或呼吸profile。

- 先看阶段及HR/ECG/ACC/RR计数，保存完整180秒或提前失败的归档；与此前约47秒断连对照。
- 需要改模式时另开一次显式 `--mode ecg` 或 `--mode hrv` 采集；若设备重启，重新唤醒后手动重跑。不要在正式实验中切换。
- 再核对TD实时曲线、持续输出、重新佩戴与独立呼吸参考。无profile时不能声称呼吸已测准，原生RR单位、输出率、断流/SQI仍须验证。

## 软件验收与剩余项

新增连接专项先取得 **7 failed / 1 passed**，修复并扩展后连同采集与P-02回归为 **143 passed in 12.06s**。覆盖扫描对象/无缓存参数、无广播、订阅失败、初始化顺序、匹配模式零重复写、差异写入、ACK隔离、模式切换断线、等待回读断线、CLI失败归档与日期封包；另保留既有RawFrame、校准、候选CLI和TD传输测试。

**尚未验证：**本机更新驱动后的持续连接效果、本次新增查询在当前固件上的实际响应、模式切换/重启行为、真实TD双通道显示、呼吸校准与真实信号质量。工具和反编译输出仅本地忽略区保留，未提交第三方APK/源码；任务状态、正式研究与GitHub不变。

## 同日模拟器动态补证

用户同意首次协议并限定仅蓝牙/定位权限后，已安装运行ECTRI V1.4.8，详见[动态记录](2026-10-20_ectri-emulator-inspection.md)。免登录可到设备页；实际扫描器注册status=0，App约20秒重启扫描，不能把这个节奏当作已连接后的保活。scan it按钮请求相机/相册，拒绝不妨碍返回BLE扫描；通知权限拒绝后仍可恢复蓝牙并重新扫描。

App自身建议电源保护、后台运行/自启动、蓝牙及位置权限/开关，另将通讯录和通话权限用于来电提醒。此次只读取建议，未开额外权限；这些是手机端进程存活建议，不证明胸带有App密钥限制或Windows此前断连根因。系统蓝牙OFF时页面仍显示Scanning，未连接前首页已有100 bpm，故SRP继续依真实数据/系统状态判断，不能消费这类页面提示当接入回执。

分段录屏447.134秒、日志和虚拟PCAP已保存；820条HCI记录中ACL包0，没有进入实体胸带GATT交换。因此本次补证只覆盖UI/权限/扫描/恢复，**不能进一步确认或否定设备拒绝连接的假设**，未凭这些观察继续修改驱动协议。
