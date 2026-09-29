# 数字媒体 (Unity像素视觉) — 角色交接文档

> SRP v2.1 | 2026/5/20—6/30 | 本文档面向数字媒体角色
> 核心职责：Unity 2D像素场景 → 旅人Sprite动画 → 粒子特效 → 演示视频 → 答辩PPT

---

## 1. 角色定位

你是团队唯一的视觉负责人。用户看到的四种天气场景、在场景中行走的旅人、飘落的雪花和雨滴——都是你的作品。你的像素画笔决定了用户的第一印象。你也是答辩的"门面担当"：PPT 和演示视频由你主导。

| 子系统 | 你的职责 | RACI |
|--------|----------|:--:|
| 情绪天气体验 | 4种天气视觉设计、旅人角色设计 | R |
| Unity 2D 视觉体验 | 场景搭建、Sprite动画、粒子特效全权负责 | R/A |
| 答辩准备 | PPT制作、演示视频、系统截图 | R/A |

---

## 2. 技术栈

| 工具 | 版本 | 用途 | 为什么 |
|------|------|------|--------|
| Unity | 6000.3.15f1+ | 2D渲染引擎 | Unity 6 LTS，原生2D支持，Sprite Renderer+Particle System成熟 |
| Aseprite | 最新 | 像素美术 | 像素画行业标准工具，支持Sprite Sheet导出 |
| C# | Unity 内置 | OSC接收/天气控制/旅人动画 | Unity 原生语言 |
| OBS Studio | 最新 | 演示视频录制 | 免费开源，支持窗口/全屏录制 |
| PowerPoint | — | 答辩PPT | 学校标配 |

### 像素规范（40-srp-2d-pixel-visual-design）

| 参数 | 值 |
|------|-----|
| 渲染分辨率 | 640×360 (16:9) |
| Sprite PPU | 32 |
| 旅人尺寸 | 32×32 px |
| 动画帧率 | 12 fps |
| 每场景色板 | ≤16 色 |

---

## 3. 七阶段任务分解

| 阶段 | 日期 | 你的任务 | 产出物 | 验收标准 | Hermes Skill |
|------|------|----------|--------|----------|-------------|
| 1 需求 | 5/20-5/25 | 四种天气视觉概念、旅人角色概念、色板确定 | 概念图、色板、参考素材 | 4色板审批通过 | 40-srp-2d-pixel-visual-design |
| 2 原型 | 5/26-6/1 | Unity 项目框架、旅人 Sprite Sheet(行走3帧)、单场景(风暴)原型 | Unity工程、旅人Sprite、风暴场景 | 旅人能动、风暴场景有雨滴粒子 | 40-srp-2d-pixel-character, 40-srp-unity-osc-runtime |
| 3 闭环 | 6/2-6/9 | 4场景全搭建、UDP接收+天气强度映射、旅人状态机 | 4场景、WeatherController.cs、TravelerAnim.cs | 天气强度能驱动粒子密度和颜色 | 40-srp-animation-state-machine, 40-srp-feedback-mapping-design |
| 4 完善 | 6/10-6/17 | 旅人全动画(保护罩/微行动)、粒子优化、场景细节 | 完整旅人Sprite Sheet、粒子系统 | 4场景全部可体验 | 40-srp-2d-pixel-visual-design |
| 5 测试 | 6/18-6/23 | 配合测试修复视觉Bug、动画流畅度优化 | Bug修复、动画优化 | 关键Bug清零 | 40-srp-animation-state-machine |
| 6 实验 | 6/24-6/28 | 实验期间视觉值守、截图收集 | 系统截图 | 4场景截图齐全 | — |
| 7 交付 | 6/29-6/30 | 演示视频(4场景各2min)、答辩PPT、视觉资产整理 | 演示视频、PPT、视觉资产 | 最终交付包 | deliverable-quality-gate |

---

## 4. 四种天气场景设计

### 风暴 🌩️（焦虑）

| 元素 | 设计 |
|------|------|
| 背景 | 暗紫渐变天空(#2d1b69→#4a3f8a)，灰色云层(Tilemap) |
| 粒子 | 雨滴 2×8px 竖线，密度高；闪电碎片 8×8px，随机闪烁 |
| 旅人 | 身体前倾行走，保护罩(虚线圆，calm>50时出现) |
| 恢复 | 雨滴密度递减，天空变亮，闪电消失，保护罩修复 |

### 炙烤 🔥（烦躁）

| 元素 | 设计 |
|------|------|
| 背景 | 橙褐渐变(#8b4513→#f4a460)，地面龟裂纹理 |
| 粒子 | 热浪波纹 4×4px 半透明，向上浮动；火星 2×2px |
| 旅人 | 缓慢行走，头顶冒汗滴(2px蓝点) |
| 恢复 | 热浪消退，冷色气流(蓝青色粒子)从左侧吹入 |

### 暴雪 ❄️（低落）

| 元素 | 设计 |
|------|------|
| 背景 | 冰蓝渐变(#4682b4→#f0f8ff)，雪白地面 |
| 粒子 | 雪花 4×4px 六角形，缓慢飘落；冰晶 6×6px |
| 旅人 | 在雪中艰难行走，脚印(Tilemap印记)留在身后 |
| 恢复 | 雪花密度递减，阳光从右上角照入，地面出现暖色 |

### 褪色 🌫️（孤独）

| 元素 | 设计 |
|------|------|
| 背景 | 灰度渐变(#808080→#d3d3d3)，物体边缘模糊 |
| 粒子 | 色彩光点 3×3px(RGB随机色)，初始密度低 |
| 旅人 | 正常行走，周围有微弱光晕 |
| 恢复 | 光点密度递增，世界从灰度逐渐恢复彩色(SpriteRenderer.color Lerp) |

---

## 5. 旅人 Sprite 规范

```
旅人: 32×32 px, 16色

状态动画:
  行走: 4帧  (12fps) → calm_index<50 时播放
  站立: 2帧  (待机呼吸) → calm_index 50-75
  保护罩: 4帧 → calm_index>50 时叠加
  微行动: 2帧 → calm_index>75 时随机触发

Sprite Sheet 布局:
  [行走1][行走2][行走3][行走4]
  [站立1][站立2][保护1][保护2]
  [保护3][保护4][微动1][微动2]
```

---

## 6. calm_index → 天气强度映射

```csharp
// WeatherController.cs
void UpdateWeather(float calmIndex) {
    if (calmIndex < 25) {
        intensity = 1.0f;   // 全强度暴风雨
        particleEmission = maxEmission;
    } else if (calmIndex < 50) {
        intensity = 0.7f;   // 中等强度
        particleEmission = maxEmission * 0.6f;
    } else if (calmIndex < 75) {
        intensity = 0.4f;   // 弱化
        particleEmission = maxEmission * 0.3f;
    } else {
        intensity = 0.1f;   // 接近晴天
        particleEmission = 0;
    }
    
    // 驱动视觉效果
    bgColor = Color.Lerp(stormColor, clearColor, 1 - intensity);
    particleSystem.emission.rateOverTime = particleEmission;
    travelerAnim.speed = 1 - intensity * 0.5f;  // 天气越强越慢
}
```

---

## 7. Unity 项目结构

```
04-Unity视觉/unity-project/
├── Assets/
│   ├── Scenes/
│   │   ├── StormScene.unity
│   │   ├── HeatScene.unity
│   │   ├── SnowScene.unity
│   │   └── FadeScene.unity
│   ├── Scripts/
│   │   ├── OSCReceiver.cs       UDP:5006 接收
│   │   ├── WeatherController.cs 天气强度→视觉映射
│   │   ├── TravelerAnim.cs      旅人Sprite状态机
│   │   └── TransitionManager.cs 天气→晴天过渡
│   ├── Sprites/
│   │   ├── traveler_sheet.png   旅人Sprite Sheet
│   │   ├── storm_bg.png
│   │   ├── heat_bg.png
│   │   ├── snow_bg.png
│   │   └── fade_bg.png
│   ├── Animations/
│   │   └── Traveler.controller  Animator Controller
│   └── Particles/
│       ├── rain_particle.png
│       ├── snow_particle.png
│       ├── fire_particle.png
│       └── color_spark.png
├── ProjectSettings/
└── Packages/
```

---

## 8. 演示视频规范

| 参数 | 值 |
|------|-----|
| 分辨率 | 1920×1080 |
| 帧率 | 30 fps |
| 录制工具 | OBS Studio |
| 场景数 | 4 段 |
| 每段时长 | 约 2min |
| 内容 | 天气从"全强度"→呼吸调节→"恢复晴天"完整过程 |
| 音频 | 可配轻音乐或保留环境音 |

---

## 9. 答辩 PPT 结构（10-12页）

| 页 | 内容 | 你的产出 |
|----|------|----------|
| 1 | 封面 | 项目名+团队+4天气缩略图 |
| 2 | 痛点 | 大学生情绪困境(数据+引用) |
| 3 | 方案 | 一句话+系统框架图 |
| 4 | 天气隐喻 | 4天气→4情绪映射表(配Sprite) |
| 5 | 架构 | 设备→Python→TD→Unity 数据流图 |
| 6 | 创新1 | 天气隐喻可视化(文献空白) |
| 7 | 创新2 | 简约旅人叙事(2026拟真反效果论文支撑) |
| 8 | 创新3 | 非严肃判断情绪教育(合规) |
| 9 | 演示 | 嵌入演示视频或GIF |
| 10 | 实验 | 实验设计+初步数据图表 |
| 11 | 结论 | 总结+未来工作 |
| 12 | 致谢 | — |

---

## 10. 对接点

| 对接方 | 你从他们获取 | 你向他们提供 |
|--------|-------------|-------------|
| SE | UDP JSON @ :5006 (weather.intensity, calm.index) | — |
| 交互设计A (TD) | 天气强度同步、提示词触发时机 | 场景预览截图 |
| 交互设计B (实验) | — | 系统截图、被试视觉反馈 |
| 全员 | — | 演示视频、PPT、视觉资产 |

---

## 11. 质量门禁

- [ ] 4个场景全部可运行
- [ ] weather.intensity 能驱动粒子密度和颜色变化
- [ ] 旅人4状态动画流畅无跳帧
- [ ] 每场景色板 ≤16色
- [ ] Sprite PPU 统一为 32
- [ ] 演示视频分辨率 1920×1080
- [ ] PPT 结构完整，包含所有创新点
