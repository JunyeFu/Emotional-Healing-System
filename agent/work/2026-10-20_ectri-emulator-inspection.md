# ECTRI 模拟器动态检查

状态：用户确认后已完成授权范围内的动态检查，走到真实Android扫描API；未发现实体胸带，未进入GATT连接，不作为真实设备接入证据。录制已结束，独立模拟器已关闭，安装及数据分区保留。

## 环境与安装

- 用户提供APK：`D:/Wecheat/xwechat_files/wxid_xhivgw8tj7kt22_8232/msg/file/2026-10/base.apk(2).1`，原件未改。
- Android aapt读回：包名 `com.manridy.ectri`，版本 `V1.4.8` / code `190`，minSdk26、targetSdk36，支持x86_64；不再使用静态资产内的缓存版本号。
- 本机Android Emulator36.5.10，新建 `SRP_ECTRI_20261020`，Android35 / Google Play / x86_64，序列号 `emulator-5560`。
- AVD及证据在 `D:/Agent/srp/agent/local/artifacts/ectri-emulator-20261020/`，独立数据分区；只在用户AVD索引新增同名INI，未覆盖其他项目实例。
- `adb install`返回Success；冷启动落到 `com.manridy.ectri/.activity.PermissionActivity`，显示耗时2664ms。当前crash buffer为空，没有观察到启动崩溃。

## 监控与当前停留点

证据目录：[本地证据](../local/artifacts/ectri-emulator-20261020/)。

| 文件 | 内容 |
|---|---|
| `01-first-launch.png` / `.xml` | 首次隐私页截图、UI树，未点击同意 |
| `ectri-inspection-01.mp4` | 当前已执行的启动段录屏，已停止并导出；不包含后续未执行流程 |
| `logcat-through-consent.log` | 截至同意页的系统/应用日志，包含SplashActivity及PermissionActivity启动记录 |
| `package-first-launch.txt` | 包信息和权限实际状态；蓝牙/定位/通讯录/通话等运行时权限均未授予 |
| `bluetooth-first-launch.txt` | 虚拟蓝牙ON及控制器状态，不是实体胸带连接回执 |
| `actions.jsonl` / `qa.py` | 本轮截图动作及按UI树取坐标的本地辅助脚本 |
| `emulator-attempt2-stdout.log` / `-stderr.log` | 当前启动与netsim参数；首次失败尝试日志另行保留 |

首次页面要求同意隐私政策和用户协议，涉及个人、健康、运动及设备信息。初次检查停在同意页；随后用户明确同意继续隔离测试、仅允许必要蓝牙/定位权限，本轮才点击同意。未注册、登录或输入身份信息。后续操作前重新开启日志与分段录屏，现均已正常停止，不声称正在后台无限监控。

首次后台logcat进程在启动阶段结束，因此追加了完整ring-buffer导出；导出包含App实际启动及当前页面记录。后续动态步骤改用可明确等待和停止的前台采集会话，不能把启动段收集器视为全程常驻。

## 蓝牙与网络边界

虚拟蓝牙状态ON，HCI版本5.3、控制器厂商224，走emulator/netsim，不是主机Realtek适配器。已配置HCI snoop full和netsim pcap，但尚无胸带连接流量；当前没有设置物理USB蓝牙透传或实体手机调试。

[Android网络说明](https://developer.android.com/studio/run/emulator-networking)提供模拟器Bluetooth能力；[AOSP netsim介绍](https://android.googlesource.com/platform/tools/netsim/+/refs/heads/master/guide/src/)将其定位为虚拟设备/配件无线网络。支持虚拟BLE不等于已连通电脑旁的实体BigRun，不能用模拟器未发现胸带判断设备拒绝。

当前netsim使用 `--pcap --no-web-ui --debug-no-network`，已配置禁止外网转发，未登录账号。ADB、模拟器gRPC、netsim端口实际仅监听loopback；gRPC8560要求token。端口登记在 `D:/Agent/全局端口注册表.md`。首轮强行指定netsim instance3与emulator默认发现不一致，导致启动重试，已停止本轮所属进程并更正参数；不把该启动问题归因于App或胸带。

## 用户确认后的动态结果

运行段：北京时间2026-10-20约19:06至19:14；模拟器日志使用UTC，动作JSONL记录UTC。`watch.py`以前台受控会话保持logcat，录屏180秒自动分段；三个视频分别180.053、180.032、87.048秒，总计447.134秒，H.264 / 540×1212。分段导出与启动之间存在短暂切换间隙，logcat持续记录。

| 操作/分支 | 实际观察 | 证据 |
|---|---|---|
| 同意→跳过引导→首页→Devices | 无需登录即可进入设备入口；未输入个人信息 | `02`至`05`截图/XML |
| 初次Add device | 申请位置与附近设备权限，授予前台精确位置及附近设备组后进入扫描 | `06`至`09`截图/XML |
| 扫描 | App PID4578调用startLeScan，扫描器注册status=0；列表未出现设备 | `logcat-20261020-190631.log:93980`、`:93988`；`09/10`截图 |
| 扫描重启节奏 | 11:07:59、11:08:19、11:08:39等，约20秒重启一轮；不是数据保活证据 | 同日志`:99920`、`:104250`等 |
| scan it按钮 | 实际触发相机/相册分支，不是BLE重扫按钮；系统权限均拒绝，选择quit回到扫描页 | `11`至`16`截图/XML |
| 扫描中关闭虚拟蓝牙 | 系统OFF，页面仍显示Scanning；不能只依页面文字判断扫描真实状态 | `17`截图及日志11:10:02关闭记录 |
| 返回并再次Add device | 出现额外通知权限请求，拒绝后仍能进入蓝牙关闭提醒 | `18`至`21`截图/XML |
| 开启蓝牙 | App说明→系统请求开启→允许，回到设备页；再次Add device可重新扫描、status=0 | `22/23/27`截图；同日志`:116552`、`:116583` |
| 稳定性说明 | 电源保护/后台运行/自启动、蓝牙及位置权限和位置开关；来电提醒的通讯录/通话权限另列 | `24/25`截图/XML；只读取、未开启额外设置 |
| 结束 | 返回Devices停止扫描，再停止监控并关闭本轮模拟器，App数据保留 | `28-finish-devices.*`、actions.jsonl |

首页在未连接任何设备、未授予蓝牙权限时已显示100 bpm，不能把该值当成真实胸带读数。新增连接逻辑仍应以原始通知和接收时间判断状态，不复制此页面的数字或扫描提示作为成功依据。

最终运行时授权只有五项：ACCESS_FINE_LOCATION、ACCESS_COARSE_LOCATION、BLUETOOTH_SCAN、BLUETOOTH_CONNECT、BLUETOOTH_ADVERTISE。后三项由Android附近设备权限组一并授予；相机、照片/视频、通知、通讯录、通话、后台位置等均为false。`package-final.txt`已核对，`crash-final.log`为空；未观察到本轮App崩溃。

## 抓包与产物核对

- 后续运行段：[第1段](../local/artifacts/ectri-emulator-20261020/ectri-20261020-190631-01.mp4)、[第2段](../local/artifacts/ectri-emulator-20261020/ectri-20261020-190631-02.mp4)、[第3段](../local/artifacts/ectri-emulator-20261020/ectri-20261020-190631-03.mp4)；`video-inspection.json`为现有ffprobe检查结果。
- `logcat-20261020-190631.log`：16,416,118字节，含所有后续页面、权限及扫描日志；包含系统历史缓冲，不是App专属日志。
- `netsim-artifacts.zip` / `netsim-capture/`：模拟器关闭后netsim自动封存。蓝牙PCAP43,701字节；Wi-Fi PCAP99,000字节。不得将虚拟流量当成实体设备流量。
- 按[tcpdump的HCI H4伪首部格式](https://www.tcpdump.org/linktypes/LINKTYPE_BLUETOOTH_HCI_H4_WITH_PHDR.html)解析蓝牙PCAP：820包，410个HCI命令、410个HCI事件，ACL包0，**没有进入可分析的GATT数据交换**。此计数覆盖整个虚拟控制器，不只属于ECTRI。
- `inspect_evidence.py` / `evidence-summary.json`：复算PCAP完整记录、最终权限集合、空crash buffer、三个视频编码/时长；执行通过，real_device_connection_test=NOT_RUN。

旧的启动段视频与失败启动日志保留。当前没有后台录制或BLE采集；5037共享ADB服务保留，5560/5561/8560/6402/59452均已释放并登记。

## 下一步

1. 实体Android手机USB调试并由操作者完成连接许可，在真正佩戴BigRun时记录App的扫描、服务发现、CCCD、初始化命令及断线原因。
2. 同样配置下对比电脑驱动；模式切换、设备接触和系统省电分别测试，不将手机后台建议直接当成Windows设备拒绝的根因。
3. 本次没有认证失败、MTU/CCCD或持续传感数据的动态证据，不据虚拟扫描通过扩大既有驱动/正式研究验收结论。

本轮未改SRP驱动、TD工程、任务状态或正式研究状态，未提交/推送GitHub。
