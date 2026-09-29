# V-04 H3 heat样片评审说明 v1.0

> 状态：`MACHINE_PASS_READY_FOR_H3_ASSEMBLY`

## 评审对象

`heat-candidate-v1`是H3输入短样片，不单独设置人工硬门。它用于检查热浪盐原中的冷流风道能否在10秒内清晰呈现4秒吸气与6秒呼气，并为最终H3合并评审提供heat片段。

## 文件

- 并列视频：`.artifacts-local/V-04/H3/heat-candidate-v1/heat-H3-paired-review.mp4`
- 场景原生：`.artifacts-local/V-04/H3/heat-candidate-v1/heat-H3-scene-native.mp4`
- 抽象提示：`.artifacts-local/V-04/H3/heat-candidate-v1/heat-H3-abstract-pacer.mp4`
- 环境声音：`.artifacts-local/V-04/H3/heat-candidate-v1/heat-H3-ambient.wav`
- 彩色关键帧：`review/H3/heat-H3-keyframes-v1.jpg`
- 灰度关键帧：`review/H3/heat-H3-grayscale-v1.jpg`
- 配置与清单：`V-04_H3_heat样片配置_v1.0.json`、`V-04_H3_heat候选清单_v1.0.json`

## 观察重点

1. 吸气时冷流目标从前中景向上聚拢，实际痕迹在近场滞后响应。
2. 呼气时冷流沿地表向右前方延伸；呼气持续时间和路径长度均明显大于吸气。
3. 4秒切换点后目标已进入呼气而实际仍短暂保持吸气，目标与实际不被自动吸附。
4. 抽象条件使用外环和内环分别表达目标与实际，不让冷流风道承担阶段提示。
5. 两条件共享背景卷动、基础热浪、盐尘、声音和累计状态；基础天气不泄露4秒阶段边界。

heat机器门通过后继续制作snow和山雾长廊输入样片。四项输入齐备后统一进入H3合并人工评审。
