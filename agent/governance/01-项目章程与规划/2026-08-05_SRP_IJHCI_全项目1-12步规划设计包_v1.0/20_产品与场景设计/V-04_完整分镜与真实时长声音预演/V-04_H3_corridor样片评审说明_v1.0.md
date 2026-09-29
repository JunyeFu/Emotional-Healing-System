# V-04 H3 山雾长廊样片评审说明 v1.0

> 候选：`corridor-candidate-v1`
> 机器门：`PASS`
> 输入门影响：`H3_INPUT_PREVIEWS_READY_PASS`

## 打开方式

- 并列评审视频：`D:\Agent\03-SRP\.artifacts-local\V-04\H3\corridor-candidate-v1\corridor-H3-paired-review.mp4`
- 场景原生参与者视频：`D:\Agent\03-SRP\.artifacts-local\V-04\H3\corridor-candidate-v1\corridor-H3-scene-native.mp4`
- 抽象提示参与者视频：`D:\Agent\03-SRP\.artifacts-local\V-04\H3\corridor-candidate-v1\corridor-H3-abstract-pacer.mp4`
- 彩色关键帧：`review/H3/corridor-H3-keyframes-v1.jpg`
- 灰度关键帧：`review/H3/corridor-H3-grayscale-v1.jpg`

## 评审重点

1. `0.00..0.30`当前天气是否自然退入山雾，不出现空白帧或提示残留。
2. `0.30..0.70`山雾长廊是否足够中性，无字界碑是否只作为环境地标经过。
3. `0.70..1.00`下一天气是否只显现中性基线，不提前暴露目标周期。
4. 左右两条件是否从头到尾完全一致，没有抽象双环或场景原生提示。
5. 风雨、风雾和雪林声音是否连续，不形成完成音或新的节律提示。

## 机器结果

| 项目 | 结果 |
|---|---:|
| 时长 / 帧率 / 帧数 | `12 s / 30 fps / 360` |
| 阶段比例 | `0.30 / 0.40 / 0.30` |
| 两条件视频SHA-256 | 均为`4987293f81c7623b9d53b2e5101530fb24e5aad943d2936254d27e49459c911e` |
| 最大条件像素差 | `0` |
| 70%前下一场景权重 | `0` |
| 30%后当前场景权重 | `0` |
| 界碑水平位移 | `230 px` |
| 声音 | `-22.31 LUFS-I / -13.21 dBTP` |

## 当前结论

Codex视觉预检和专项机器门均为`PASS`。至此H2参考片段、storm、heat、snow和山雾长廊五项输入已齐，下一步装配不超过2分钟的H3合并评审视频并输出四天气六节点Unity交接分镜。当前不构成V-04完成或Unity运行证据。
