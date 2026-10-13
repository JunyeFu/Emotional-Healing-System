# Storm 双环线宽调整预览

- 输出：[v2 PNG](storm-double-ring-v2.png)，1603×981，RGB 合成预览。
- 参考：[v1](storm-double-ring-v1.png)。通过内置 AI 生图编辑加粗两环线条，保留居中、空心、浅蓝和外清内淡的关系。
- 仅调整外观预览，不覆盖 v1，不变更 Unity 运行参数。提示词中的增幅是生成指导，不是像素实测值。

## 实际提示词

```text
Edit the provided Storm screenshot preview with exactly two concentric pale blue translucent outline circles. Make ONE small change only: slightly increase the stroke width of BOTH circular outlines, about 35% thicker than the reference, so the rings are a little easier to read but remain delicate, highly translucent and unfilled. Preserve the exact ring diameters, concentric center position, spacing, pale blue color and opacity hierarchy: the outer ring remains more visible / less transparent, the inner ring remains fainter / more transparent. Do not increase glow or brightness. Preserve the rainy scene, rain streaks, water ripples, horizon, camera framing, aspect ratio and background colors. No new objects, no extra rings, no labels, no fill, no vignette. Only modestly thicken the existing ring strokes. Keep output at least at the reference resolution.
```
