# U-05 规范化实际范围

## 原文迁移

来源基线为16fa5ad。CleanAndRebuildScenes.cs及meta、CleanupWeatherDuplicates.cs及meta从Unity Assets/Scripts/Editor迁入本包archive。专项逐文件读取Git原字节，与归档实际字节比较一致；类名及GUID没有其他活动C#、unity、prefab或asset引用。

不执行旧菜单，不删除或修改HeatScene、SnowScene，不修改F-03/G-02历史资产扫描。活动Editor程序集少了两个旧菜单，Unity6000.4.9f1回归实跑105项通过；完整根目录及其余旧工具清理尚未完成。

## 当前实现核对

HeatScene与SnowScene都有Traveler、MainCamera、PromptDisplay、WeatherParticles、Background，无m_Script引用。旧场景存在不证明本包有U01RuntimeBridge、V03SceneAdapter、步骤实例驱动、实际render_receipt或性能结果。B没有绑定，不按文件名认领旧场景。

## 依赖与责任

V-02负责A/B/C互斥绑定；U-03负责模板验收；U-08负责目标设备与性能规格及后续集成。注册表显示U-08依赖U-05，而U-05 AC3消费U-08预算，当前需先落实规格提供方式，不能把整包DONE作为提供规格的前置。这里只登记缺口和交接方式，不新建已冻结里程碑、不改状态。

领取人、分支与复核人仍为空；其他进行中和复核中的分发输入未改。本轮自动检查不构成实际天气或真人签收，U-05保持WAIT_DEP。
