# 证据④ 降级演示录像说明

## 产物
- **视频：** `V03_degradation_demo.mp4`（163 KB，120 帧 / 12 fps，10 s，960×600）
- **帧序列：** `frames/frame_0000.png ~ frame_0119.png`（120 张 PNG，每阶段 24 帧）
- **演示程序：** `player/V03DegradationDemo.exe`（Development Build，非正式天气接线）

## 演示流程（按钮/自动按序切换，每阶段停留 24 帧）
| 帧区间 | 阶段 | 四层实际表现（屏幕只读面板） |
|---|---|---|
| 0–23 | GOOD | target ContinueTarget；actual Full opacity=1.000 conf=0.93；recovery 未锁、低通跟随；fallback marker=None certainty=0.930 |
| 24–47 | DEGRADED | target 继续；actual Degraded opacity=0.575；recovery 继续低通；fallback LowCertainty certainty=0.620 |
| 48–71 | UNUSABLE | target OpenLoopTarget；actual Unavailable opacity=0.350 static；recovery **locked=True out 冻结=0.550**；fallback TemporarilyUnavailable certainty=0 |
| 72–95 | DISCONNECTED | 无帧路径 NotifyLinkDown：target phase=none 并 Abort；actual 静态；recovery 锁定保持；无伪造成功 |
| 96–119 | ResetSession | 会话边界重置：recovery **locked=False out=0.000**；background segChanges 1→2；这是唯一解锁路径 |

## 验证的 AC 点
- **AC1（层级隔离）：** 每阶段只改对应层字段，屏幕面板逐帧显示四层独立输出。
- **AC2（锁定/解锁）：** UNUSABLE/DISCONNECTED 触发锁定，输出冻结；quality 变化不解锁；仅 ResetSession 解锁（locked True→False）。
- **AC3（诚实降级）：** DISCONNECTED 无伪造成功，applied 计数不再增长；certainty=0；背景全程零节律。

## 复现命令
```powershell
# 1. 生成演示场景（Unity batchmode）
Unity.exe -batchmode -projectPath <project> `
  -executeMethod SRP.V03.DevTools.V03DemoBuild.CreateScene -quit

# 2. 构建演示程序（FormalBuildGate 要求开发构建授权）
$env:SRP_F03_DEV_BUILD_AUTHORIZED='1'
Unity.exe -batchmode -projectPath <project> `
  -executeMethod SRP.V03.DevTools.V03DemoBuild.BuildPlayer `
  --v03-out=<out_dir> -quit

# 3. 自动截图并退出
V03DegradationDemo.exe --v03-capture=<frames_dir> --v03-auto-quit `
  -screen-width 960 -screen-height 600

# 4. 合成 MP4
ffmpeg -framerate 12 -i frames/frame_%04d.png `
  -c:v libx264 -pix_fmt yuv420p V03_degradation_demo.mp4
```

## 说明
- 演示驱动 `V03DegradationDemoDriver` 位于 `Assets/Scripts/V03/DevTools/`，
  Editor 构建入口位于 `DevTools/Editor/`（SRP.V03.DevTools.Editor asmdef，仅 Editor）。
- 仅为取证工具，未改动正式天气管线，未触碰 WeatherController/UDPReceiver/SpoutReceiver。
