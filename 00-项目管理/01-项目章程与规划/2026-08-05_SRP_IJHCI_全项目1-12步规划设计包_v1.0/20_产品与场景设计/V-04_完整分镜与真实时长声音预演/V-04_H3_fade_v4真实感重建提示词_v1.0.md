# V-04 H3 fade v4真实感重建提示词 v1.0

> 日期：`2026-08-31 +08:00`
>
> 用途：固定镜头`fade`背景候选重建，不生成语义提示、角色、界面或运行时效果。

## 1. 三景画风提取

`storm`、`heat`和`snow`共同采用清晰的近景表面细节、可辨认的材质粗糙度、稳定的自然光方向、接触阴影、分层大气透视和克制色彩。旧`fade`的问题不是细节数量不足，而是植被轮廓重复、岩体过度光滑、河床石均匀铺排和水面过于洁净，导致塑料化与生成痕迹。

## 2. 最终有效提示词

```text
Use case: photorealistic-natural
Asset type: SRP Unity fade-weather fixed-camera background preview
Primary request: A genuinely photorealistic wide landscape photograph of a calm clear river running through a humid subtropical limestone karst valley, suitable as a high-end realistic game environment background.
Scene/backdrop: Broad natural river with clear shallow foreground water revealing naturally sorted river stones beneath the surface. Irregular low banks on both sides with mixed native grasses, ferns, shrubs, exposed damp soil, mossy wet rock, and a few mature willow-like riparian trees. Weathered limestone karst peaks recede in multiple layers toward the distance, with geologically plausible fractures, erosion channels, mineral staining, ledges, and patchy vegetation rather than vegetation covering every surface. Open blue late-morning sky with naturally illuminated cumulus clouds.
Composition/framing: Wide 16:9 fixed camera, eye level just above the river surface, approximately 28mm full-frame lens. Water fills the lower half. A broad unobstructed central water corridor continues toward the middle-right distance. The lower-left foreground remains open shallow water for later actual-feedback visuals. Banks frame the view but do not close it. Clear foreground, middle ground, and several distant landform bands suitable for later layer separation. No central island.
Lighting/mood: Neutral physically plausible late-morning daylight, realistic sun direction, contact shadows, ambient bounce, natural dynamic range, restrained highlights, subtle aerial perspective, no cinematic color grade.
Materials/textures: Real photographic microtexture and imperfection. Water has accurate refraction, Fresnel reflection, overlapping nonuniform ripples, depth-dependent clarity, faint suspended particles, and soft caustics. River stones vary greatly in geology, scale, color, wetness, algae, orientation, spacing, and burial depth. Vegetation varies in species, age, leaf size, orientation, translucency, damage, density, and wind posture. Limestone has rough granular surfaces, cracks, erosion, strata, mineral variation, moss, and irregular plant attachment.
Color palette: Natural blue sky, neutral green vegetation with realistic variation, gray-beige limestone, muted brown-gray river stones, clear water reflecting sky and banks. Balanced saturation.
Constraints: No people, animals, architecture, bridge, dam, boat, road, central island, fantasy object, text, logo, UI, or watermark. Deep focus across the scene.
Avoid: CGI look, 3D cartoon, game concept art, painterly or oil-paint texture, illustration, sculpted smooth cliffs, foliage blobs, repeated leaf curls, identical pebbles, tiled textures, waxy rocks, glass-sheet water, turquoise fantasy water, excessive saturation, bloom, HDR halos, oversharpening, fog washout, depth-of-field blur.
```

## 3. 当前结果边界

当前输出为`1672x941`、`TEMP_REFERENCE_ONLY`候选，SHA-256为`c230185de7a47245c54b5383f9fa643ce46e737497e01065c2cabdde6e075491`。该图用于确认背景构图和真实感方向；透明切层、Unity导入与许可放行仍由后续门禁完成。
