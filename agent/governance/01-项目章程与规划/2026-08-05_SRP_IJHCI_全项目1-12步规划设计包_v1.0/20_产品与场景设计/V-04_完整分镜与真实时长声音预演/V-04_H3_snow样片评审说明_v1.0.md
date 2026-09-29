# V-04 H3 snow样片评审说明 v1.0

> 状态：`MACHINE_PASS_READY_FOR_H3_ASSEMBLY`

## 评审对象

`snow-candidate-v1`是H3输入短样片，不单独设置人工硬门。它用于检查雪雾松林中的粉雪升沉能否在10秒内以同强度镜像方式呈现5秒吸气和5秒呼气，并为最终H3合并评审提供snow片段。

## 文件

- 并列视频：`.artifacts-local/V-04/H3/snow-candidate-v1/snow-H3-paired-review.mp4`
- 场景原生：`.artifacts-local/V-04/H3/snow-candidate-v1/snow-H3-scene-native.mp4`
- 抽象提示：`.artifacts-local/V-04/H3/snow-candidate-v1/snow-H3-abstract-pacer.mp4`
- 环境声音：`.artifacts-local/V-04/H3/snow-candidate-v1/snow-H3-ambient.wav`
- 彩色关键帧：`review/H3/snow-H3-keyframes-v1.jpg`
- 灰度关键帧：`review/H3/snow-H3-grayscale-v1.jpg`
- 配置与清单：`V-04_H3_snow样片配置_v1.0.json`、`V-04_H3_snow候选清单_v1.0.json`

## 观察重点

1. 吸气时中景目标粉雪向上、向外展开；呼气时同一组粉雪沿镜像状态路径下降、收拢。
2. 两阶段粒子数量、透明度、垂直行程和缓动一致，不通过增亮或增加粒子强调任一方向。
3. 近景实际粉雪独立升沉；5秒切换点目标已进入呼气，实际仍处于吸气。
4. 抽象条件只使用外环和内环，不保留相位锁定粉雪，也不增加背景雪补偿。
5. 两条件共享背景卷动、基础降雪、林间雾、声音和累计状态；背景不泄露5秒或10秒周期。

snow机器门通过后只剩山雾长廊输入样片。该输入通过后关闭`H3_INPUT_PREVIEWS_READY`并装配H3合并人工评审视频。
