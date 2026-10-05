# fade 全幅褪色补充预览

- 图片：[全幅黑白版](fade-fully-desaturated.png)，1672×941 RGB PNG。
- 参考：[复色中段](fade-weather.png)；内置 AI 生图编辑，新增文件，不覆盖既有八张。
- 村庄与双环均呈灰度外观，保留明暗层次、固定构图和外环更清晰的关系；代表起始状态的视觉示意。
- AI 输出存在微小 RGB 通道差异，不声称逐像素精确零饱和度；实际 Unity 起始状态仍按既有合同使用零饱和度。

## 实际提示词

```text
Edit the provided fade village preview. Make only one change: COMPLETELY DESATURATE THE ENTIRE FRAME to true neutral grayscale, saturation exactly zero. Every part must be achromatic, INCLUDING both circular outlines: sky, river, grass, trees, path, windmill, house and rings. Neutral black-and-white grayscale only, no remaining blue, green, yellow or brown; no sepia, cool tint or color accent. Ideally every pixel's R, G and B values are equal. Preserve the original luminance, natural brightness, highlights, shadows, contrast and readable depth; do not darken the scene or introduce a gloomy filter. Preserve exactly the same composition, camera, scenery geometry, ring diameters, ring stroke widths and opacity hierarchy (outer clearer than inner), both rings still unfilled. No added text, objects, fog, vignette, borders or weather particles. Keep original aspect ratio and resolution. This depicts the fully desaturated initial state, not mid-restoration.
```
