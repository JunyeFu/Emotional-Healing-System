# fade 深蓝加粗双环预览

- 图片：[新预览](fade-blue-rings-v2.png)，1672×941 RGB PNG。
- 本轮以全褪色 fade 图为底，按用户要求将环线宽翻倍、改深蓝并增加透明感；环的位置、直径与空心形式不变，外环比内环更清晰。
- 灰度背景保留，但双环按本轮新要求为蓝色。原全幅灰度版与另外八图均未覆盖，正式合同和 Unity 参数不改。
- AI 合成图不含可编辑 alpha；翻倍和透明度增加30%是提示词目标，未当作精确像素测量。生成后针对描边偏实补做一次透明感调整。

## 初次提示词

```text
Edit only the TWO concentric breathing-circle outlines in the provided fully desaturated village preview. Make both outline strokes TWICE as thick as their current widths, keeping each ring's centerline diameter, circular shape, center position and spacing unchanged. Change the outlines from gray/white to a slightly deeper muted blue, approximately #477DA8, not navy-black, neon cyan or bright electric blue. Make the rings about 30% MORE TRANSPARENT than before: reduce their apparent overlay opacity to about 70% of its previous value, do NOT increase opacity. Preserve the established hierarchy: outer ring is slightly clearer / less transparent than inner. Both remain unfilled and easy to see but allow the scenery underneath to show through. No glow, no filled disc, no band between the circles, no text or tick marks. Everything EXCEPT the two ring outlines must remain fully grayscale: do not recolor any grass, sky, river, windmill, house, paths or trees. Preserve background brightness, shadows, camera framing and composition. Keep the existing aspect ratio and output resolution. One edited image, not a comparison layout.
```

## 透明感修订提示词

```text
Make one precise correction to this image: the blue circle strokes currently look too solid. Preserve both thick stroke widths, exact circle diameters, center, spacing, and muted deeper blue hue. Make the two ring strokes visibly translucent so underlying background detail shows THROUGH the stroke itself. Target visual alpha around 0.35 for the OUTER stroke and 0.25 for the INNER stroke, so outer stays a little clearer and inner is more transparent. They must not be solid opaque blue borders. Do not thin the strokes, do not change circle size, do not add glow or fill. Preserve the entire grayscale village background, geometry, camera and luminance exactly. Only reduce opacity of the two blue outlines. One landscape image at the same resolution.
```
