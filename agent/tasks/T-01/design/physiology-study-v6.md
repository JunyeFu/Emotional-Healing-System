# 全过程生理信号与Unity状态流模拟

## 设计判断

不存在一套适用于所有人的“标准生理数据”。本交付提供文献和设备规格约束下、可重复生成的合成测试数据，不把某个波形、心率、幅度或噪声水平当作人群标准。

当前研究为A固定开环、B原生受限适应；I共同理想、G有效下发、X从信号提取的实际估计独立保存。800秒仍为候选，本次用于覆盖四模块和全部流程分支，不修改正式方案和参数。

## 来源与取舍

1. McSharry等（2003），ECGSYN，DOI 10.1109/TBME.2003.808805。使用NeuroKit2已安装的ECGSYN实现生成PQRST及搏间变化，不再使用固定周期尖峰拼接。
   原文：https://archive.physionet.org/physiotools/ecgsyn/paper/
   代码与说明：https://physionet.org/content/ecgsyn/1.0.0/
2. Polar官方H10 SDK规格：ECG为130Hz、微伏；HR/RR通知与连续心电是不同数据对象。本合成源的RR从ECG检峰产生，属于Python衍生估计，不冒充设备RR通知。
   https://github.com/polarofficial/polar-ble-sdk/blob/master/documentation/products/PolarH10.md
3. PLUX官方respiBAN规格：呼吸400Hz/28位、运动16位；呼吸上升对应吸入、下降对应呼出，停留附近并非理想绝对平台。采用胸带相对幅度、缓慢漂移及噪声，不转换成气流或肺容积。
   https://support.pluxbiosignals.com/knowledge-base/respiban-ble-getting-started/
   https://support.pluxbiosignals.com/knowledge-base/respiban-ble-sample-signals/
4. NeuroKit的BreathMetrics讨论明确区分气流与胸带形态。本任务不直接将气流模拟函数作为胸带原始值。
   https://github.com/neuropsychology/NeuroKit/issues/543
   https://neuropsychology.github.io/NeuroKit/functions/ecg.html
5. 慢呼吸综述提供节律背景，不证明本项目某个天气、顺序或参数有效，也不提供个人必然变化曲线。
   https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2018.00353/full

## 可直接复用的数据

每组含raw.npz、unity-state.jsonl、manifest.json。原始样本指未经过本项目滤波的合成传感器域值，不是厂商BLE通知字节，也不通过伪造ADC值或字节包声称完成D-01/D-02。

| 对象 | 设置 | 性质 |
|---|---|---|
| 心电 | 130Hz，ECGSYN，均值72bpm、波动参数2，幅度乘900 | 72、2、900为工程fixture参数，不是引用得到的推荐值 |
| 呼吸 | 400Hz，相对幅度，胸廓升降/停留/补吸形态 | 个体振荡器有7%周期偏差、相位扰动和幅度漂移，不直接令X=G |
| 加速度/角速度 | 三轴，400Hz，m/s²及rad/s；含重力与运动片段 | 与呼吸共采样为测试配置，真实SDK通道速率及换算须实测 |
| RR及HR | 从合成ECG检峰计算；RR毫秒，HR每分钟 | 非独立随机数；RR为离线检峰结果，只按时间释放已有结果 |
| 呼吸X | 因果低通和0.2秒差分，固定工程阈值 | 不读取I/G；质量差时未知；不是S-02正式算法或补吸识别验收 |
| Unity状态 | 10Hz，场景/段/步骤/运行暂停/模拟回执 | 模拟Unity端点，不证明画面渲染或正式协议兼容 |

三组分别是A完整、B完整、A中止。完整流程四天气各200秒，分25/150/25秒；有效320秒处暂停10秒，原始采集不断。中止组有效400秒退出。准备期曲线可见但不写实验记录。

240至248秒加入运动干扰，460至465秒呼吸/运动缺失以null保存，465至467秒标记恢复质量不足。心电继续，不能把单设备断流当成全设备离线。没有预设心率必然下降、HRV必然提高或量表必然改善。

本版ECG与胸带振荡器没有联合拟合呼吸性搏间调制，不能用它验证跨信号耦合或HRV对呼吸的效应。质量标签来自已知注入片段，而非经过真实数据校准的SQI；界面数值SQI继续留空。信号算法与研究指标的效度不能由本模拟自证。

I按天气设计的3-3-3-3、4-6、5-5、2.5-1.5-6产生。A保持G=I。B在周期边界依据上一实际估计选择1或1.05倍周期，仅用来测试G与I分离及记录能力，是显式工程测试策略，不是已冻结自适应方案。

## 分工与导出

- Python：生成原始样本、因果呼吸粗估计、离线ECG检峰、RR/HR及描述统计。正式在线与离线分析仍归S/A任务，不在TD重复维护算法。
- TD：设备曲线、状态和源时间显示；逐场开发记录；当前/历史已结束场次CSV及ZIP导出。滤波、质量阈值或研究结论不由TD临时决定。
- 导出含samples.csv、events.csv、summary.json；缺失是空单元，不补零。源样本时间与TD接收单调时间分列，RR的ms不改成分秒；实验用时显示分:秒。
- samples.csv保留各采样点和运动轴，HR/RR为该包当前估计，不能把重复保持值当成新的心搏。要做HRV应使用raw.npz内逐搏rr_t/rr_ms，或重新对ECG分析。
- 当前开发记录不能替代P-02正式原始归档；正式采集仍应由Python持久化，不依赖TD打开。

## 运行

```powershell
py -3.14 -X utf8 agent/tasks/T-01/execution/study_simulation.py agent/local/artifacts/physiology-study-20261008
py -3.14 -X utf8 agent/tasks/T-01/execution/capture_workbench.py --study agent/local/artifacts/physiology-study-20261008
py -3.14 -X utf8 agent/tasks/T-01/execution/verify_study.py <本轮证据目录> agent/local/artifacts/physiology-study-20261008
```

生成目录须为新的目录；已存在的数据不覆盖。回放默认5倍速，曲线保持原采样率和源时间轴，界面明确显示回放速度。加速测试回答数据/界面流程能否贯通，不回答实时硬件延迟。验证逐样本核对输入与TD记录、CSV计数、缺失、独立会话和Unity状态帧，不只看截图曲线是否好看。

给回放命令加`--speed 1`可按原速度发送。截图检查点会短暂停留在固定源帧，以便检查瞬时故障；因此这套交互检查仍不是连续实时延迟基准。普通开发数据最多100毫秒同步一次，生命周期事件立即同步；异常断电下这一开发缓存窗口不应被描述为正式P-02耐久保证。
