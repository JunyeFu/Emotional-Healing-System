# U-06 规范化范围与消费者影响

## 原文与活动工程

以38d2fb1为迁移前基线。FinalBuild、FinalRebuild、ComprehensiveFix三脚本及meta原文迁入archive；专项逐文件比较Git原字节相同，并确认text属性为unset。类名及GUID无活动C#/unity/prefab/asset消费者；不执行旧菜单。

旧脚本会把Assets/Sprites全量设为Point/32 PPU，清空并保存旧场景。当前归档避免它们继续出现在生产菜单，不修改既有素材、HeatScene/SnowScene、默认构建设置及F-03开发构建。专项核对两个旧天气场景字节未变；共享Unity6000.4.9f1 EditMode105/105通过。

F-03/G-02资产扫描中的旧路径是历史记录，保留，不回写；当前正式资产许可仍需下游审查。U-04/U-05共享归档保留单一原件，不重复复制。

## 构建现状

默认EditorBuildSettings只启用SampleScene；三项旧Final/Fix菜单没有BuildPipeline.BuildPlayer，不能作为制品证明。F-03实际开发构建显式生成F03DevReplayBuild并使用Development选项，声明formal_use_allowed=false；本轮仅阅读，不重新构建。最终天气集成、场景清单和独立成品仍归U-08。

## 任务拼合

A/B/C三包当前均未明确分配，不通过排除法给C指定snow。V-02需落实互斥完整绑定，U-03需先验收模板。U-08预算规格与整包集成分开提供，本轮只登记依赖缺口，不改注册表或冻结里程碑。

U-06实际负责人、Play、Profiler、参数、声音、真实回执和签收仍缺；状态保持WAIT_DEP，其他冻结包未改。当前目录清理和共享测试不等于天气或正式构建验收。
