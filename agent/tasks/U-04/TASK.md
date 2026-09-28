# U-04 剩余天气A四层适配器

## 当前状态与责任

WAIT_DEP，依赖U-03、V-03，约4人日，过程配置P-DEV。实际领取人、分支及复核人为空。U-03公共模板未验收；V-02当前与历史入口均未明确把剩余天气A绑定到某个技术ID。不能按文件名或默认storm代替分配。

## 交付及验收

交付V-02实际分配的一个天气SceneAdapter、四层参数、音频响应与测试场景。

- AC1技术ID、场景及核心机制与V-02分配一致，核心机制可辨识。
- AC2四层独立、降级可见，不修改U-03公共模板。
- AC3目标设备帧率、内存、加载和声音达到U-08冻结预算；没有预算时不得填写通过。

必需证据为Play录像、Profiler报告、截图组、参数表和模板漂移检查。历史StormScene与样片不等于本包新适配器。

## 四天过程与阶段出口

1. 由V-02确认A的唯一技术ID及U-05/U-06剩余分配，实际领取人核对U-03已验收模板、V-03映射和V-04有效素材。出口为明确对象与可用输入，不把提议当冻结。
2. 在共享Unity工程复用模板组装一个固定镜头天气，完整底图配独立RGBA素材；通过扩展点实现差异，不改SceneAdapter公共合同或Python顺序。出口为本天气可运行场景和参数。
3. 接入v2.2周期、步骤身份及Target/Actual/Recovery/Fallback，保持Actual独立、累计锁定和背景非周期；在同源开发fixture下验证双条件交接、暂停中止与质量四态。出口为分层检查、真实控制及渲染回执。
4. 在目标设备采集Play、Profiler、截图和声音结果，按U-08预算核对；完成模板漂移检查与复核后交接U-07/U-08。出口为真实运行证据及按要求签收，不用合成验证关闭场景验收。

## 技能与资料

Unity、粒子、Shader、音频及Profiler。国内入口沿用[Unity中文学习](https://learn.unity.com/?locale=zh_CN)与[Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)，学习Prefab、粒子系统、材质、Audio Mixer及Profiler对应章节。资料版本不替代工程ProjectVersion。

## 当前执行入口

[适配器交接](outputs/current-adapter.md)、[来源](inputs/sources.json)、[验证](execution/verify.ps1)。本轮只做任务规范化、旧工具清理和共享程序集回归，不代领任务，不把WAIT_DEP改为DONE。
