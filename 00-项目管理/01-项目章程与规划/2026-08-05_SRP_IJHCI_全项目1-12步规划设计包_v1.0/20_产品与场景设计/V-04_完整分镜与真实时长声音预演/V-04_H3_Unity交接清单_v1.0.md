# V-04 H3 Unity交接清单 v1.0

> 用途：V-05全旅程灰盒和后续Unity实现的进入条件。

## 1. 输入权威

- [ ] 读取`V-04_H3_四天气六节点Unity交接分镜_v1.0.json`，不得从评审视频反推时长或状态。
- [ ] 读取P-01 manifest、段状态和控制事件；Unity不拥有顺序、时钟或正常结束条件。
- [ ] 读取V-03四层映射合同；目标、实际、累计环境状态、降级与背景保持独立。
- [ ] `storm`和`fade`的核心相位动画仅在F-05 v2.2签收后进入正式字段绑定；此前fixture必须显式标记为开发用途。
- [ ] 四种天气的演示周期身份和完整六节点正式交接均等待F-05 v2.2及消费者迁移；Unity不得本地计数或推断第一/第二周期。
- [ ] 所有素材通过G-02许可门后才进入正式构建；当前V-04图像与声音均为`TEMP_REFERENCE_ONLY`。

## 2. 建议实现顺序

1. 建立共享`WeatherModuleView`，只接收`ApplyTarget`、`ApplyActual`、`ApplyRecovery`、`ApplyFallback`、段状态和控制事件。
2. 建立两种提示条件切换，确保只替换目标/实际载体，不复制场景、声音和时钟。
3. 实现`demo`第一周期隐藏实际、第二周期淡入实际的共同规则；实际数据从模块开始持续记录。
4. 实现模块基线与`closed_loop`累计输入门；段边界不重置目标或实际。
5. 分别实现storm、heat、snow、fade唯一核心机制；其余天气运动保持非周期背景。
6. 实现两级可见降级：低确定性、暂不可用；禁止填零或把目标复制成实际。
7. 实现共享山雾长廊，确保两条件同帧相同且不绑定固定天气对。
8. 用四模块golden trace运行六节点截图、回执和录像，再进入完整灰盒评审。

## 3. 每天气最低实现面

| 天气 | 必做目标 | 必做实际 | 必做累计 | 额外边界 |
|---|---|---|---|---|
| `storm` | 四阶段雨幕风门 | 近场气流雨丝 | 雨势与路径能见度 | 停留阶段无漂移；等待F-05 v2.2 |
| `heat` | 4秒汇集、6秒贴地推进 | 近场冷流盐尘 | 热霭与远景清晰度 | 呼气依靠时长和行程，不使用亮度或卷轴奖励 |
| `snow` | 5-5确定性镜像粉雪 | 近场粉雪痕迹 | 雪雾与树线清晰度 | 固定种子/轨迹；吸呼粒子数量与显著度对称 |
| `fade` | 第一吸主潮、补吸第二峰、长呼回流 | 近场断续色丝 | 轮廓与纹理慢变量 | 固定镜头；整屏复色独立于呼吸和累计；等待F-05 v2.2 |

## 4. 两条件公平检查

- [ ] 同一manifest、天气顺序、段边界、目标、实际、累计、降级和输入帧。
- [ ] 同一背景、相机/卷轴、非周期天气、环境声、暂停位置和转场。
- [ ] `scene_native`只开启场景目标/实际载体；`abstract_pacer`只开启外环/内环。
- [ ] 抽象条件中的场景机制保持中性，不泄露呼吸周期。
- [ ] 目标和实际不吸附；Unity不根据视觉距离计算累计值。
- [ ] fade整屏复色在两条件同值、同曲线、同时间，不在步骤边界变速。

## 5. 六节点证据

每个天气、每种条件都保存六个节点证据，但不是六个节点都生成F-01渲染回执。F-01 `render_receipt`必填字段为`schema_version/message_type/receipt_id/session_id/event_id/frame_seq/unity_frame/rendered_monotonic_ns/module_id/segment/result/error_code`；只允许绑定已ACK的`segment`控制，且`module_id/segment`与控制载荷一致。

节点证据另外记录`cue_mode/build_hash/screenshot_path/telemetry_frame_seq`，不得用`module_index/weather_id/timestamp_ns`冒充F-01回执字段：

- [ ] `ENTRY`：应用当前模块`segment=demo`后，保存ACK、绑定该控制的渲染回执和首帧；目标可见、实际隐藏、累计基线。
- [ ] `DEMO_END`：保存`demo`最后遥测帧和截图；当前目标/实际连续、累计仍为基线，不生成额外渲染回执。
- [ ] `CLOSED_LOOP_START`：应用当前模块`segment=closed_loop`后，保存ACK、绑定该控制的渲染回执和首帧；同相位连续，累计输入门已打开。
- [ ] `CLOSED_LOOP_MID`：保存当前遥测帧和截图；目标、实际、累计和降级可独立核对，不生成额外渲染回执。
- [ ] `CLOSED_LOOP_END`：先保存`closed_loop`最后帧，再保存当前模块`segment=lock_transition`的ACK及渲染回执；最后合法实际和累计锁定，无理想终点补齐。
- [ ] `TRANSITION_COMPLETE`：先保存当前`lock_transition`最后帧。非末模块保存下一模块`module`与`segment=demo`的ACK，并让回执绑定下一模块`demo`；第四模块只保存`end` ACK，不为`end`生成渲染回执。

## 6. 故障和运行检查

- [ ] 暂停冻结卷轴、目标、实际、累计插值、环境噪声时间和声音位置；恢复从同一状态继续。
- [ ] 重复控制事件不重复推进画面；错序或错session消息拒绝且不污染当前状态。
- [ ] `DEGRADED`只改变实际确定性；`UNUSABLE/DISCONNECTED`冻结最后合法实际并锁定累计。
- [ ] 未收到实际步骤时不猜测；fade缺少补吸时不生成第二股实际色丝。
- [ ] TouchDesigner缺席时完整参与者体验仍可运行。
- [ ] 正式路径不接受Mock、零值补齐、未许可素材或未跟踪素材。

## 7. 退出条件

V-05可以在本清单、H3人工确认和所需上游合同关闭后建立全旅程灰盒。后续Unity任务仍须分别形成Edit Mode、Play Mode、Windows制品、四模块golden trace、故障注入、无TouchDesigner运行、资产许可和真实设备联调证据；V-04样片不能替代这些证据。
