# V-04 H2 candidate-v9 独立视觉预审报告 v1.0

## 预审对象

| 字段 | 值 |
|---|---|
| 候选 | `candidate-v9` |
| 配置 | `V-04_H2样片配置_v1.2.json` |
| 清单 | `V-04_H2候选清单_v1.2.json` |
| 设计合同 | `V-04_H2_candidate-v9_色潮回流设计合同_v1.0.md` |
| 预审角色 | Codex独立视觉预审，不代替团队总监 |
| 预审结论 | `READY_FOR_TEAM_DIRECTOR_REVIEW` |
| H2状态 | `PENDING_HUMAN_CONFIRMATION` |
| 日期 | `2026-08-29 +08:00` |

本报告只判断样片是否达到提交团队总监观看的最低质量，不代填团队总监九项结论。

## 返工记录

第一轮v9渲染的近景实际反馈仍表现为较长连续亮线，具有悬浮轨迹观感，独立预审将`native_naturalness`判为`REVISE`。该轮媒体和清单已移动到Git忽略目录`.artifacts-local/V-04/H2/rejected/candidate-v9-r1/`，不属于当前候选。

当前候选将实际层改为水面内的断续水平反光片，并将补潮改为低透明度窄核心与反光片段组合。时间、背景、整屏复色、卷动、声音和抽象双环没有改变。

## 九项预审

| 评审键 | 独立预审 | 证据与观察 |
|---|---|---|
| `first_frame` | `PRECHECK_PASS` | 两条件首帧`color_u=0`，平均色度均为0，无彩色闪帧 |
| `final_color` | `PRECHECK_PASS` | 9.50秒与9.97秒`color_u=1`，恢复`fade-B`原生颜色；该值不表示累计状态达到1 |
| `continuity` | `PRECHECK_PASS` | 整屏颜色使用单一SmoothStep曲线；两条参与者视频无黑帧或持续1秒冻结；时间接触表未见步骤边界闪切 |
| `phase_legibility` | `PRECHECK_PASS` | 第一吸主潮、补吸附加分支和长呼下游位移在彩色及灰度评审图中位置和形状可区分；长呼头部路径551.659像素 |
| `native_naturalness` | `PRECHECK_PASS` | 当前原生提示无矩形区、平行通道或悬浮连续线；目标和实际alpha均未越出水面遮罩；最终自然感由团队总监观看视频裁定 |
| `actual_fidelity` | `PRECHECK_PASS` | 目标补吸开始时实际仍为`INHALE_1`，延迟后才进入`INHALE_2`；无自动补造第二股实际反光 |
| `condition_match` | `PRECHECK_PASS` | 提示掩膜外最大原始像素差为0；两条件复用同一背景、复色、卷动、时间和声音 |
| `audio_scroll` | `PRECHECK_PASS` | 声音为共享48 kHz/24-bit双声道PCM源，`-22.24 LUFS-I/-3.49 dBTP`；卷动固定且不读取步骤 |
| `H2` | `PENDING_TEAM_DIRECTOR` | 只有团队总监观看并明确提交九项结果后才能判定`PASS`或`REVISE` |

## 机器门摘要

| 指标 | 结果 |
|---|---:|
| 目标/实际越出水面最大alpha | `0 / 0` |
| 第一吸目标面积 | `49156 px` |
| 补吸主潮保留率 | `0.995748` |
| 补吸新增面积 | `13642 px` |
| 补吸/第一吸面积比 | `1.273273` |
| 长呼头部路径 | `551.659 px` |
| 长呼质心下游位移 | `188.946 px` |
| 终点目标残留面积比 | `0.0` |
| 三阶段最小灰度差 | `24.507` |
| 条件提示掩膜外最大差 | `0` |

`validate_v04_h2_v9.py`对媒体哈希、格式、色彩包络、水面裁切、三步骤几何、实际步骤忠实度、灰度提示、声音和条件一致性给出`PASS`。

## 团队总监评审入口

- 并列视频：`.artifacts-local/V-04/H2/candidate-v9/fade-H2-paired-review.mp4`
- 场景原生视频：`.artifacts-local/V-04/H2/candidate-v9/fade-H2-scene-native.mp4`
- 抽象提示视频：`.artifacts-local/V-04/H2/candidate-v9/fade-H2-abstract-pacer.mp4`
- 彩色关键帧：`review/H2/fade-H2-keyframes-v9.jpg`
- 灰度关键帧：`review/H2/fade-H2-grayscale-v9.jpg`

当前证据只覆盖10秒设计预演，不构成Unity运行、正式构建、真实设备链、H2人工通过或V-04完成。
