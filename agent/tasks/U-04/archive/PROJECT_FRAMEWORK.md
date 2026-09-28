# SRP Weather Visual — Unity 2D 工程框架

> v2.1 — 2026/6/22 | Unity 6000.4.9f1 | URP 2D

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│  Python 信号处理 (mock_data / Polar H10)            │
│  UDP :5005 → TD Prototype    UDP :5006 → Unity     │
├─────────────────────────────────────────────────────┤
│  TouchDesigner (呼吸引导圈)                         │
│  Spout → Unity SpoutReceiver (背景纹理层)           │
├─────────────────────────────────────────────────────┤
│  Unity URP 2D (本工程)                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Weather  │  │ Traveler │  │ Background (5段) │  │
│  │ Controller│  │ Animator │  │ 左→右 无缝拼接   │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 粒子系统 │  │ 提示词   │  │ BreathHUD (待)   │  │
│  │ 雨/闪/雪 │  │ 浮现/消散│  │ 双圈呼吸引导     │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 场景结构

### StormScene (已完成) — 风暴天气

```
StormScene
├── MainCamera
│   ├── Camera: orthographic, size=6, bg=(0.08,0.08,0.15)
│   └── UniversalAdditionalCameraData: no postProcess, no AA
├── BackgroundContainer
│   ├── bg_01 (x=0)        ← 桥面+前景荒地
│   ├── bg_02 (x=+21.333)  ← 左→右排列
│   ├── bg_03 (x=+42.667)
│   ├── bg_04 (x=+64.0)
│   └── bg_05 (x=+85.333)
│   Sprite: 1672×941px @ 32PPU, scale=0.408 → 21.333×12 units
├── Traveler (x=7.467, y=-1.594)
│   ├── SpriteRenderer: sortingOrder=0
│   ├── Animator → Traveler.controller
│   └── Shield (child)
│       └── SpriteRenderer: sortingOrder=5, 初始隐藏
├── WeatherSystem (空容器)
└── Controllers
    ├── Scene1Director
    ├── UDPReceiver
    └── WeatherController
```

### 其他场景
- **HeatScene** — 炙烤天气场景文件已建立，需继续校准热浪/色彩恢复机制
- **SnowScene** — 暴雪天气场景文件已建立，需继续校准雪势/脚印机制
- **FadeScene** — 褪色天气场景文件已建立，需继续校准重新上色机制

## 美术资产

| 类别 | 路径 | 内容 | 配置 |
|------|------|------|------|
| 背景 | `Sprites/backgrounds/bg_01~05.png` | 5段夜景无缝拼接 | 32PPU, Point, No Compression |
| 旅人 | `Sprites/traveler/` | idle, lookdown, walk_01~06, pose×4, fall×8 | 32PPU, Point, No Compression |
| 盾牌 | `Sprites/traveler/shield/` | shield_00~08, clean, cracked | 32PPU, Point, No Compression |
| 特效 | `Sprites/effects/` | lightning_full, rain_drop, speed_trail | 32PPU, Point, No Compression |

## 动画系统

### AnimatorController: Traveler.controller

| 状态 | 动画 | 触发参数 | 帧 |
|------|------|----------|:--:|
| Idle | Idle.anim | (默认) | 1 |
| Walk | Walk.anim | — | 6 @ 8fps |
| Lookdown | Lookdown.anim | — | 1 |
| Fall | Fall.anim | — | 1 |
| Kneel | Kneel.anim | Kneel (trigger) | 1 |
| Run | Run.anim | Run (trigger) | 1 |
| Sit | Sit.anim | Sit (trigger) | 1 |
| Stand2 | Stand2.anim | — | 1 |
| Shield | Shield_Appear.anim | — | 1 |
| Shield_Clean | Shield_Clean.anim | ShieldClean (trigger) | 1 |
| Shield_Cracked | Shield_Cracked.anim | ShieldCrack (trigger) | 1 |

### 动画技术细节
- 所有 AnimationClip 使用 ObjectReferenceKeyframe + GUID+fileID 精灵引用
- Walk: 6帧 @ 8fps, 0.75s 循环
- 姿势动画: 单帧定格

## 空间坐标

| 元素 | 位置 | 尺寸 |
|------|------|------|
| Camera viewport | X=[-10.667, +10.667] Y=[-6, +6] | 21.333×12 |
| bg_01 中心 | (0, 0) | 21.333×12 |
| 桥面世界Y | -2.531 | 28.9% from bg bottom |
| 前景荒地中点 | X≈+7.467 (85% from left) | — |
| Traveler | (7.467, -1.594) | targetH=1.875 (0.75x) |
| Traveler 脚底Y | -2.532 | bridge surface |

## 运行时数据流

```
Python UDP:5006 → UDPReceiver.cs
  → WeatherController.OnDataReceived(json)
    → weather.intensity → 粒子强度/背景色
    → breath.phase → 呼吸引导圈
    → scoring.calm_index → 旅人动画切换
    → prompt trigger → PromptDisplay
```

## Editor 脚本索引

| 脚本 | MenuItem | 用途 |
|------|----------|------|
| UpdateAllArtAssets | SRP/Update ALL Art Assets (Full Rebuild) | 全量一键重建 |
| EdgeDetectBridge | SRP/Edge-Detect Bridge | 桥面检测+旅人定位 |
| ScaleTravelerAndScene | SRP/Scale Traveler and Scene | 旅人0.75x缩放+GameView |
| AnalyzeBridge | SRP/Analyze Bridge Surface | 桥面颜色剖面分析 |
| FindBridgeSurface | SRP/Find Bridge & Place Traveler | 多列中值检测桥面 |
| PlaceTravelerOnBridge | SRP/Place Traveler on Bridge Surface | 亮度跳跃桥面定位 |
| VerifyTravelerPosition | SRP/Verify Traveler Position | 旅人位置日志 |
| FinalBuild | SRP/Final Build Scene 1 | 场景构建 |
| BuildScene1 | SRP/Build Scene 1 | 场景构建变体 |
| BuildScene2D | SRP/Build 2D Scene | 2D场景构建 |
| SetupWeatherScenes | SRP/Setup Weather Scenes | 多天气场景 |
| CleanAndRebuildScenes | SRP/Clean and Rebuild Scenes | 清理重建 |
| ConfigureSpriteImports | SRP/Configure Sprite Imports | 精灵导入配置 |
| CreateAnimations | SRP/Create Animations | 动画创建 |
| ImportNewSprites | SRP/Import New Sprites | 新精灵导入 |
| ArrangeBackgrounds | SRP/Arrange Backgrounds | 背景排列 |
| FixScene1 | SRP/Fix Scene 1 | 场景修复 |
| FixBlackScreen | SRP/Fix Black Screen | 黑屏排查 |
| FixGameView | SRP/Fix GameView Resolution | GameView修复 |
| ComprehensiveFix | SRP/Comprehensive Fix Scene | 综合修复 |
| FinalRebuild | SRP/Final Rebuild | 最终重建 |
| DebugCamera | SRP/Debug Camera Setup | 相机判断 |
| DiagTest | SRP/Diagnostic Test | 通用判断 |
| DiagURP | SRP/Diagnose URP Pipeline | URP判断 |
| DiagQuality | SRP/Diagnose Quality Settings | Quality判断 |
| DiagSprites | SRP/Diagnose Sprites | 精灵判断 |
| PlayModeDiag | SRP/Play Mode Diagnostic | Play模式判断 |
| PixelChecker | SRP/Pixel Perfect Check | 像素验证 |
| RenderCameraToFile | SRP/Render Camera to File | 渲染到文件 |
| SwitchToForwardRenderer | SRP/Switch to Forward Renderer | 渲染器切换 |
| TestSprite | SRP/Test Sprite Render | 精灵渲染测试 |
| TestScene | SRP/Test Scene | 场景测试 |

## 已知问题

| # | 问题 | 状态 |
|---|------|:--:|
| K1 | Play Mode 渲染状态需复测 | 🟡 |
| K2 | execute_code Windows "文件名或扩展名太长" | 🔴 (用MenuItem规避) |
| K3 | HeatScene/SnowScene/FadeScene 已建文件但机制未完成验收 | 🟡 |
| K4 | BreathHUD 双圈像素HUD未实现 | ⬜ |
| K5 | ScriptableObject 天气配置未创建 | ⬜ |
| K6 | 旅人姿势动画未接入Scene1Director时间线 | ⬜ |

## 关键配置

| 配置项 | 值 |
|--------|-----|
| Unity版本 | 6000.4.9f1 |
| 渲染管线 | URP |
| 目标分辨率 | 1920×1080 |
| 精灵PPU | 32 |
| 精灵Filter | Point (no filter) |
| 精灵Compression | None |
| Camera orthographicSize | 6 |
| 工作流模式 | Editor Script + [MenuItem] |
| 版本控制 | Git (main branch) |
