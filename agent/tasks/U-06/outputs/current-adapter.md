# U-06 当前剩余天气C交接

状态WAIT_DEP，实际领取人与复核人未落实。C没有绑定，不能默认snow或在A/B也未分配时自行推算最后一个天气。U-03选fade，余下storm、heat、snow由V-02给出互斥完整的A/B/C分配；共用缺口见U-04/U-05当前入口，本包不新造设计冻结。

## 实现对象与职责

确认对象后复用U-03公共模板，读取V-02当前场景、V-03映射及Python v2.2配置。storm雨幕风门按吸3/停3/呼3/停3表达两个独立hold；heat冷流风道按吸4/呼6；snow粉雪升沉按吸5/呼5。四天气完整demo均使用步骤和周期身份，不因heat/snow只有两步而退回粗相位合同。

固定镜头、无横向背景或视差、无屏幕内旅人；完整底图配独立RGBA素材，环境音不增加呼吸或失败提示。Target来自Python步骤，Actual来自独立交互状态估计及置信度；Recovery累计锁定不因同模块换段或GOOD恢复解开，Background非周期，Fallback只控制Actual可用性。暂停冻结画面及音轨，恢复仍由Python推进。

双条件同背景、声音、时轴、算法及累计函数；场景目标/实际相位载体和抽象双环互斥。U-06负责本天气及条件接口，U-07推广抽象四结构，不让U-07反向阻塞U-03最小对照。U-01控制桥区分ACK与真实render_receipt，U-02提供只读四层和生命周期；公共模板不在本包重写。

## 旧实现与过期生产工具

SnowScene与HeatScene当前是旅人、相机、提示占位、粒子和背景，没有m_Script绑定，不含U-01控制桥或V03SceneAdapter。仅有文件和旧“ready”文字不代表当前适配器完成；旧场景未在本轮改写。

FinalBuild、FinalRebuild、ComprehensiveFix三菜单会把Assets/Sprites全量重导入为Point/32 PPU，再清空并保存旧四天气或StormScene，创建旅人和旧背景；两个StormScene重建工具还附加旧Scene1Director。源码没有BuildPipeline.BuildPlayer，它们不是Windows成品构建入口。确认活动类名/GUID无消费者后，三脚本及meta原文移出Assets归档，不再编译和注册菜单；不继续用这些Final/Fix名称覆盖当前模板或高精度背景。

ProjectSettings/EditorBuildSettings当前仅启用SampleScene。现有F-03开发构建明确生成F03DevReplayBuild场景并使用Development选项，不靠默认列表，也是非正式DEV-REPLAY。保留默认设置与已验收F-03工具；最终天气入口、构建候选及无TD完整体验由U-08继续实现和验收。本轮没有运行构建、替换默认场景或声称制品可用。

## 上下游与当前缺口

V-02分配、U-03模板、真实领取人和本天气运行均未完成；需要Play、Profiler、截图、参数、声音及模板漂移证据。U-08整体依赖U-06，而U-06 AC3需要U-08预算，先落实目标设备和预算规格，再消费集成结果；当前不定阈值、不改依赖、不代填新里程碑完成。

U-04至U-06合起来只覆盖三个不同剩余天气，不重复认领、不遗漏。U-07消费双条件接口，U-08消费视听/性能、最终场景清单和构建，G-02/G-05负责素材许可及活动资格。既有F-03/G-02历史扫描保留原路径快照，不改历史证据；U-04/U-05归档继续引用原位置，避免重复保留多套当前工具。
