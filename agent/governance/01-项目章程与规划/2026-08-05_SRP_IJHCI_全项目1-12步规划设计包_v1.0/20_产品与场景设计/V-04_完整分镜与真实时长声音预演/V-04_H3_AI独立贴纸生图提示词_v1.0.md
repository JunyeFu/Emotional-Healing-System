# V-04 H3 AI独立贴纸生图提示词 v1.0

## 通用前缀

```text
Use case: stylized-concept
Asset type: one Unity fixed-camera weather-scene independent transparent asset
Primary request: Create exactly one complete isolated environment object or effect named by the current asset entry.
Style/medium: high-fidelity realistic 3D game environment assets, physically based materials, production concept render quality, matching the supplied scene reference.
Scene/backdrop: genuinely transparent background only.
Composition: one complete centered asset, generous transparent margin, no shared ground plane and no cropped edges.
Constraints: preserve the reference image's lighting direction, color temperature, material realism and weather identity; no text, labels, borders, white sticker outline, watermark or complete landscape; each item must remain usable independently in Unity.
```

八个素材的顺序严格对应`V-04_H3_AI独立贴纸素材清单_v1.0.json`。每项单独调用一次生成；只使用对应天气的已签收固定底图作为画风参考，不把底图作为编辑目标。评审用`4 x 2`贴纸母版在八项文件验收后确定性排版生成。

## Storm补充

```text
Subjects from left to right, top row then bottom row: a wide translucent rain-gate curtain; near-field airflow streaks; a soft rain-curtain overlay patch; a valley mist patch; a wet dark-rock cluster; wind-bent alpine grass; a narrow runoff stream; a rain-splash ripple cluster. Match the storm mountain-pass reference with cold overcast daylight, wet PBR surfaces and restrained cyan-gray atmosphere.
```

## Heat补充

```text
Subjects: a wide cool-air channel ribbon; near-field cool airflow streaks; a heat-haze distortion patch; a dust wisp; a salt-crust cluster; a pale desert-rock cluster; a shallow-channel light glint; sparse cooling particles. Match the bright salt-basin reference with dry PBR minerals and high natural daylight.
```

## Snow补充

```text
Subjects: a vertical powder-lift column; a near-field powder response; a snow-mist patch; a drifting-snow ribbon; a snow-covered pine branch; a snow-and-rock cluster; a falling powder cluster; a settling powder cluster. Match the bright alpine snow reference with crisp cold daylight and realistic granular snow.
```

## Fade补充

```text
Subjects: a flowing color-tide ribbon; a broken actual reflection trace; a water-ripple patch; a soft reflected-light patch; a riverbank grass cluster; a wet-pebble cluster; a subtle color-bloom patch; a tributary glint. Match the clear mountain-river reference with realistic water optics, natural green vegetation and bright daylight.
```
