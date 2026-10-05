# 村庄融合四天气：八张配对预览提示词

日期：2026-10-05。按用户本轮要求，以 `3.mp4` 首帧的同一村庄布局制作新候选，不自动替换现有已确认四场景底图。

## 构图与配对

- 固定河岸步道视角：左侧河流/风车，中部道路，右侧木构房屋；去掉原视频手柄、射线、菜单和圆形遮罩。
- 每种天气两张：空场景保留该天气的地表和光照，无天气粒子与双环；天气版增加对应大气效果和 v2 浅蓝空心双环，外环更清晰、内环更透。
- fade 空场景是原彩统一母版；天气版是全屏复色中段的低饱和静态示意，不代表完整动画或起始帧。
- 顺序：先生成 fade 空母版，以它生成另外三个空场景；每张天气版再引用对应空场景和双环样式。八张分别生成，不用拼图替代单图。
- AI 编辑用于方案预览，场景布局目视对齐，不承诺逐像素相同或可直接相减提取图层。

## 图片入口

| 天气 | 空场景 | 场景＋天气＋双环 |
|---|---|---|
| storm | [空场景](storm-empty.png) | [天气版](storm-weather.png) |
| heat | [空场景](heat-empty.png) | [天气版](heat-weather.png) |
| snow | [空场景](snow-empty.png) | [天气版](snow-weather.png) |
| fade | [空场景](fade-empty.png) | [天气版](fade-weather.png) |

## 实际生成提示词

### fade 新增全幅褪色版

新增 [全幅黑白预览](fade-fully-desaturated.png) 和 [实际编辑提示词](fade-fully-desaturated.md)。原彩、中段与全幅褪色三份均保留；双环在新增图中同步呈灰度，不另加压暗滤镜。

后续按新要求增加 [深蓝加粗双环版](fade-blue-rings-v2.png) 及 [两次实际提示词](fade-blue-rings-v2.md)：灰度背景保留，双环改为更宽、深蓝且更通透的外观。旧版本不覆盖。

八张均已用内置 AI 生图工具独立生成并保存为 1672×941 RGB PNG，已逐张目视检查；文件解码、四组配对和八个图片链接检查通过。所有图像仅为静态候选预览，不改变任务状态或签收范围。

### fade 空场景／统一母版

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the edit target and village geometry reference.
Remove ALL XR controllers, laser rays, simulator labels, instruction buttons, floating panels and their shadows from the input screenshot. Reconstruct the obscured path and grass naturally. Use this clean village view as the canonical master for the entire eight-image series. Full rich yet natural color: healthy green vegetation, clear blue river, pale blue sky, warm wood and stone detail. Calm daylight. No weather particles, atmospheric mist, dust, rain, falling snow, ring overlays or other UI. Empty means empty of people/UI/weather effects, not empty of buildings and terrain.
```

### storm 空场景

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the canonical clean village and exact geometry reference.
Convert only surface condition and lighting to an overcast rainy-day setting WITHOUT airborne weather effects. Muted cool blue-gray cloudy sky, wet dark soil on the path, damp grass, moist roof and wood, subtle existing-ground puddles and river reflections. Buildings and trees remain clearly readable. No rain streaks, fog curtains, lightning, particles, breath cues or UI rings. Do not erase vegetation or flood/change the river.
```

### storm 场景＋天气＋双环

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the corresponding storm clean plate and exact edit target. Image 2 supplies ONLY double-ring visual styling, not its empty rainy backdrop.
Preserve the storm clean plate geometry and add natural slanting rainfall at multiple depth scales, restrained low river mist and small ripple splashes only on water and existing puddles. Use the cloudy cool lighting; keep house and windmill visible. Avoid lightning, full-screen flashes and blue glowing horizon lines. Add exactly TWO concentric, centered, unfilled pale icy blue outline circles in screen space, matching the supporting double-ring reference. Large outer diameter about 70% of image height and inner diameter about 53%; modest stroke width like reference v2. Both highly translucent, OUTER LESS TRANSPARENT / slightly clearer than INNER. Flat UI perfect circles, not rings in perspective. No dark disc, fill, tick marks, text or additional rings. Ring appearance and position should be the same in all four weather images. Natural weather motion implied in a still frame must not form a second breathing-phase cue.
```

### heat 空场景

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the canonical clean village and exact geometry reference.
Convert only surface condition, vegetation appearance and lighting to a hot dry summer day WITHOUT airborne weather effects. Grass becomes subdued straw-green and ochre rather than neon green, path dry and light dusty tan with fine surface texture, same river retains blue water, warm hard daylight and pale bright sky. No new desert, salt basin, fire, lava or altered architecture. No shimmer, floating dust, haze ribbons, rain, snow or UI rings. Preserve all objects and their positions.
```

### heat 场景＋天气＋双环

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the corresponding heat clean plate and exact edit target. Image 2 supplies ONLY double-ring visual styling.
Preserve the heat clean plate geometry and add subtle ground-level heat shimmer above the path and distant bank, a thin natural warm atmospheric haze and sparse fine suspended dust near the ground. Keep detailed village terrain and river readable, no flames or orange screen wash. Add exactly TWO concentric, centered, unfilled pale icy blue outline circles in screen space, matching the supporting double-ring reference. Large outer diameter about 70% of image height and inner diameter about 53%; modest stroke width like reference v2. Both highly translucent, OUTER LESS TRANSPARENT / slightly clearer than INNER. Flat UI perfect circles, not rings in perspective. No dark disc, fill, tick marks, text or additional rings. Ring appearance and position should be the same in all four weather images. Natural weather motion implied in a still frame must not form a second breathing-phase cue.
```

### snow 空场景

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the canonical clean village and exact geometry reference.
Convert only surfaces and lighting to winter WITHOUT airborne weather effects. Settled soft snow on the same roofs, ground, bank rocks and tree branches. The original path route remains legible as a lightly snow-covered trail. Same trees, buildings and river remain in place; river stays open dark blue with snowy banks, not completely frozen. Cool blue-gray shadows, soft daylight, detailed snow texture, no featureless whiteout. No falling flakes, blowing snow, fog particles or UI rings.
```

### snow 场景＋天气＋双环

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the corresponding snow clean plate and exact edit target. Image 2 supplies ONLY double-ring visual styling.
Preserve the snow clean plate geometry and add gentle falling snow with varied fine flakes at natural depth scales, a small amount of low drifting powder along the bank and restrained winter haze. Avoid blizzard, opaque snow walls and any patterned breathing-phase particle cluster. Keep windmill and house visible. Add exactly TWO concentric, centered, unfilled pale icy blue outline circles in screen space, matching the supporting double-ring reference. Large outer diameter about 70% of image height and inner diameter about 53%; modest stroke width like reference v2. Both highly translucent, OUTER LESS TRANSPARENT / slightly clearer than INNER. Flat UI perfect circles, not rings in perspective. No dark disc, fill, tick marks, text or additional rings. Ring appearance and position should be the same in all four weather images. Natural weather motion implied in a still frame must not form a second breathing-phase cue.
```

### fade 场景＋褪色天气＋双环

```text
Use case: lighting-weather / compositing. Produce ONE landscape image, not a collage or contact sheet, 16:9 composition, high-resolution detailed game environment. Lock the SAME camera and scenery geometry across this series: river along the left foreground, central earthen footpath receding into the middle distance, the recognizable timber windmill left of center on the far bank, the same large steep-gabled timber house on the right, same trees, grass borders, rocks and horizon. Keep the windmill, house, path and river in the exact same positions and scale as the canonical reference. Refined high-quality 3D game materials, believable light, readable near/mid/far depth; preserve the village identity, do not substitute a different landscape. No people, controllers, hands, VR mask, floating menus, labels, text, watermarks or additional buildings. Do not change camera pose, crop or object layout.
Image 1 is the full-color canonical fade clean plate and exact edit target. Image 2 supplies ONLY double-ring visual styling.
Show a static MID-RESTORATION preview of the fade module, not the completely gray first frame: uniformly reduce saturation of the entire village scene to about 35% of original while preserving original luminance, sunlight, shadows and layout. The village remains bright and readable, with subtly muted greens, blue water and warm timber. Very delicate natural low haze over the river only, not a dark depressing filter. No left-right split, color bands, red-blue filters, permanent painted color trails or vignette. Add exactly TWO concentric, centered, unfilled pale icy blue outline circles in screen space, matching the supporting double-ring reference. Large outer diameter about 70% of image height and inner diameter about 53%; modest stroke width like reference v2. Both highly translucent, OUTER LESS TRANSPARENT / slightly clearer than INNER. Flat UI perfect circles, not rings in perspective. No dark disc, fill, tick marks, text or additional rings. Ring appearance and position should be the same in all four weather images. Natural weather motion implied in a still frame must not form a second breathing-phase cue.
```
