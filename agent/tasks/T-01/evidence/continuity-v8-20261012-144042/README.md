# 六种曲线连续性与参数标注核对

2026-10-12，TouchDesigner 2025.32820。84 秒连续模拟输入，包含一次两秒空值、一次两秒缺包；准备页不产生实验录制。14 张原生页面截图、38 项逐曲线/轴的像素和标注核对通过，详细数值见 [核对结果](continuity-verification.json)。

| 曲线 | 已知输入 | 标注与显示结果 |
|---|---|---|
| 呼吸 | 400 Hz；0.2 Hz 正弦；相对幅度 0.1—0.9 | 30 秒窗，单位为相对幅度，连续显示与缺口通过 |
| ECG | 130 Hz；1 Hz 校准正弦；幅值约 ±1000 μV | 6 秒窗，量程 ±1200 μV，连续显示与缺口通过 |
| 加速度 | X ±2、Y ±3、Z 9.81±0.5 m/s² | 三轴独立量程及颜色，原值保持；连续显示与缺口通过 |
| 角速度 | X ±0.5、Y ±0.25、Z ±0.1 rad/s | 三轴独立量程及颜色；连续显示与缺口通过 |
| RR 间期 | 60000/HR，单位 ms | 30 秒窗；趋势、底部数值及缺口一致 |
| 心率 | 72±6 bpm，20 秒周期 | 30 秒窗；趋势、底部数值及缺口一致 |

这些是数学上已知的绘图校准输入。ECG 校准正弦与 HR/RR 趋势分别测试不同显示通道，HR 不从这个正弦波检测；它们不作为同一参与者的生理记录。完整生理演练仍使用上一轮 study-v6 的输入。

截图入口：

- [连续呼吸与 ECG](02-continuous-0.png)
- [三轴加速度与 RR](03-continuous-1.png)
- [三轴角速度与心率](04-continuous-2.png)
- [呼吸与 ECG 空值缺口](07-missing-0.png)
- [缺包后的三轴与 RR](11-dropped-1.png)
- [恢复后的当前曲线](13-recovered.png)
- [新版候选工程](T01_Workbench_A.continuity-v8.candidate.toe)

所有整页 PNG 实际为 1280×720。文件名中的 1600/1920 是请求布局尺寸，不能作为对应分辨率的整页原生截图验收；报告中的 large_page_native_export_verified 为 false。曲线独立 PNG 与报告记录了各自实际像素尺寸。恢复后，30 秒窗口内的旧缺口仍保留，直到移出窗口。

重跑：

```powershell
py -3.14 agent/tasks/T-01/execution/capture_workbench.py --continuity
py -3.14 agent/tasks/T-01/execution/verify_continuity.py agent/tasks/T-01/evidence/<新运行目录>
```
