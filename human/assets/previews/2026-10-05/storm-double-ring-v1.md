# Storm 浅蓝双环外观预览

- 输出：[预览 PNG](storm-double-ring-v1.png)，1603×981，RGB 合成画面。
- 来源：用户 `0.mp4` 约 3 秒处截图；使用内置 AI 生图工具编辑，未修改源视频。
- 外观：画面中心两条浅蓝空心大环；外环透明度较低、更清晰，内环更透。没有文字、填充或圆形黑边遮罩。
- 用途：外观预览，不是带独立 alpha 的双环素材，也不冻结 U-03/U-07 运行半径、线宽、颜色或时序参数。提示词中的不透明度数值是生成指导，不是对输出的像素测量。

## 实际提示词

```text
Use case: compositing. Edit target: the provided screenshot extracted at approximately 3 seconds from the user's implemented Storm video. Generate a high-resolution visual mockup, preserving this exact dark blue rainy background, its rain streaks, horizon, ground ripples, original composition and aspect ratio. Change only by adding exactly TWO large concentric circular OUTLINE rings precisely at the image center. Both rings are pale icy light blue (#BDE7FA), highly translucent, clean smooth anti-aliased outlines with NO fill. Outer target ring diameter approximately 66% of image height; inner actual ring diameter approximately 47% of image height. Outer ring is LESS TRANSPARENT than the inner ring: approximately 28% stroke opacity for outer (72% transparent), approximately 17% stroke opacity for inner (83% transparent). These values are appearance guidance for this mockup only. Both remain subtle and allow the rain scene to remain readable. Even thin strokes, roughly 3 to 4 pixels at 2048-pixel-wide output; minimal delicate glow, no thick luminous bloom. Produce the highest available resolution, preferably at least 2048 pixels wide, without changing scene framing. Perfect continuous circles, not ellipses or perspective rings. Preserve the background brightness and colors. Do not add text, labels, arrows, numbers, tick marks, a third ring, a dark disc, a filled band, a vignette, a VR circular mask, controllers, or any new scenery. This is a screenshot-based UI appearance preview, not a standalone transparent ring asset.
```
