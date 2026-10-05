# 四天气 V3 双环统一图片集

日期：2026-10-05。当前村庄系列统一包，共九张：四天气版、四空场景，以及 fade 全褪色版。旧试作仍保留在原文件夹，不混入本包。

## 图片

| 天气 | V3 天气版 | 无圈空场景 |
|---|---|---|
| storm | [阴雨](storm-weather-v3.png) | [湿润底图](storm-empty.png) |
| heat | [热霭](heat-weather-v3.png) | [干热底图](heat-empty.png) |
| snow | [飘雪](snow-weather-v3.png) | [积雪底图](snow-empty.png) |
| fade | [复色中段](fade-weather-v3.png) | [原彩底图](fade-empty.png) |

fade 另附 [全褪色背景＋V3 蓝圈](fade-fully-desaturated-v3.png)。全褪色图直接使用上一轮 V3 样式参考，背景灰度、圈保留蓝色；空场景原样复制，不新增呼吸圈。

## 统一样式

- 使用上一轮 V3 作为同一参考：加粗空心双环，中间蓝，外环更清晰、内环更透。
- 四张天气图通过内置 AI 生图编辑，仅要求更改圈，不改天气、村庄布局、机位与色彩。
- 首张生成的线条偏细，未采用；后续四份提示词补充要求：替换旧细线，1672 像素宽画面使用约 8–10 像素的粗描边，并保留外清内淡。这是生成指导，不是运行参数。
- 预览合成 PNG 不含可编辑 alpha；颜色与不透明度数字为生成指导，不是正式 Unity 参数或像素一致性承诺。

## 实际提示词

### storm

```text
Use case: precise-object-edit / compositing. Image 1 is the ONLY edit target, the storm village-weather preview. Image 2 is ONLY the V3 double-ring style reference; do NOT copy its grayscale scenery. Replace the existing two ring outlines in Image 1 with the V3 style shown in Image 2. Match Image 2's thicker line widths, centered concentric circular geometry, diameters and spacing, gentle midpoint blue approximately #82B2D1, and highly translucent appearance. Outer ring remains a little clearer / less transparent than inner. Use visual opacity guidance around 0.30 outer and 0.21 inner. Remove the old outlines completely, no ghost rings; exactly TWO clean closed circles, no third ring. Both unfilled, no glow, no labels, no ticks, no vignette, no dark disc. Preserve ALL scenery from Image 1: exact camera framing, village buildings, windmill, trees, river, path, weather particles, lighting, color grading and saturation. Do not gray out the storm background or change its weather. Changes are confined to the two outlines. One 1672x941 landscape image, not a collage. IMPORTANT: Image 1 has OLD THIN strokes that must be replaced, NOT retained. The new outlines must be visibly about TWICE as thick as those old strokes, approximately 8 to 10 pixels wide at 1672 pixels image width, matching the thick bands in Image 2. Both circles use this thicker band, with their opacity still low and inner fainter. This is essential: do not output the old 3 to 4 pixel thin outlines.
```

### heat

```text
Use case: precise-object-edit / compositing. Image 1 is the ONLY edit target, the heat village-weather preview. Image 2 is ONLY the V3 double-ring style reference; do NOT copy its grayscale scenery. Replace the existing two ring outlines in Image 1 with the V3 style shown in Image 2. Match Image 2's thicker line widths, centered concentric circular geometry, diameters and spacing, gentle midpoint blue approximately #82B2D1, and highly translucent appearance. Outer ring remains a little clearer / less transparent than inner. Use visual opacity guidance around 0.30 outer and 0.21 inner. Remove the old outlines completely, no ghost rings; exactly TWO clean closed circles, no third ring. Both unfilled, no glow, no labels, no ticks, no vignette, no dark disc. Preserve ALL scenery from Image 1: exact camera framing, village buildings, windmill, trees, river, path, weather particles, lighting, color grading and saturation. Do not gray out the heat background or change its weather. Changes are confined to the two outlines. One 1672x941 landscape image, not a collage. IMPORTANT: Image 1 has OLD THIN strokes that must be replaced, NOT retained. The new outlines must be visibly about TWICE as thick as those old strokes, approximately 8 to 10 pixels wide at 1672 pixels image width, matching the thick bands in Image 2. Both circles use this thicker band, with their opacity still low and inner fainter. This is essential: do not output the old 3 to 4 pixel thin outlines.
```

### snow

```text
Use case: precise-object-edit / compositing. Image 1 is the ONLY edit target, the snow village-weather preview. Image 2 is ONLY the V3 double-ring style reference; do NOT copy its grayscale scenery. Replace the existing two ring outlines in Image 1 with the V3 style shown in Image 2. Match Image 2's thicker line widths, centered concentric circular geometry, diameters and spacing, gentle midpoint blue approximately #82B2D1, and highly translucent appearance. Outer ring remains a little clearer / less transparent than inner. Use visual opacity guidance around 0.30 outer and 0.21 inner. Remove the old outlines completely, no ghost rings; exactly TWO clean closed circles, no third ring. Both unfilled, no glow, no labels, no ticks, no vignette, no dark disc. Preserve ALL scenery from Image 1: exact camera framing, village buildings, windmill, trees, river, path, weather particles, lighting, color grading and saturation. Do not gray out the snow background or change its weather. Changes are confined to the two outlines. One 1672x941 landscape image, not a collage. IMPORTANT: Image 1 has OLD THIN strokes that must be replaced, NOT retained. The new outlines must be visibly about TWICE as thick as those old strokes, approximately 8 to 10 pixels wide at 1672 pixels image width, matching the thick bands in Image 2. Both circles use this thicker band, with their opacity still low and inner fainter. This is essential: do not output the old 3 to 4 pixel thin outlines.
```

### fade

```text
Use case: precise-object-edit / compositing. Image 1 is the ONLY edit target, the fade village-weather preview. Image 2 is ONLY the V3 double-ring style reference; do NOT copy its grayscale scenery. Replace the existing two ring outlines in Image 1 with the V3 style shown in Image 2. Match Image 2's thicker line widths, centered concentric circular geometry, diameters and spacing, gentle midpoint blue approximately #82B2D1, and highly translucent appearance. Outer ring remains a little clearer / less transparent than inner. Use visual opacity guidance around 0.30 outer and 0.21 inner. Remove the old outlines completely, no ghost rings; exactly TWO clean closed circles, no third ring. Both unfilled, no glow, no labels, no ticks, no vignette, no dark disc. Preserve ALL scenery from Image 1: exact camera framing, village buildings, windmill, trees, river, path, weather particles, lighting, color grading and saturation. Do not gray out the fade background or change its weather. Changes are confined to the two outlines. One 1672x941 landscape image, not a collage. IMPORTANT: Image 1 has OLD THIN strokes that must be replaced, NOT retained. The new outlines must be visibly about TWICE as thick as those old strokes, approximately 8 to 10 pixels wide at 1672 pixels image width, matching the thick bands in Image 2. Both circles use this thicker band, with their opacity still low and inner fainter. This is essential: do not output the old 3 to 4 pixel thin outlines.
```
