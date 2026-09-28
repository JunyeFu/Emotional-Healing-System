# U-05 剩余天气B四层适配器

## 当前状态与责任

WAIT_DEP，依赖U-03、V-03，约4人日，过程配置P-DEV。实际领取人、分支及复核人为空。B没有V-02明确分配，不能按列表第二项把B当作heat；剩余候选为storm、heat、snow。U-03模板未验收，本轮规范化不代领或解锁任务。

## 交付与验收

交付V-02实际分配的一个天气SceneAdapter、四层参数、音频响应及测试场景。

- AC1技术ID及概念与V-02分配一致，核心机制可辨识。
- AC2Target、Actual、Recovery、Fallback独立，降级可见，不修改U-03公共模板。
- AC3目标设备帧率、内存、加载与声音符合U-08预算；预算缺失时记录待验收，不自行填阈值。

必需Play录像、Profiler报告、截图组、参数表、模板漂移检查。旧HeatScene或SnowScene的文件、设计预演及共享EditMode均不是本包适配器验收。

## 四天过程与阶段出口

1. 对齐：由V-02确认A/B/C互斥且完整的技术ID分配，落实实际领取人，消费U-03已验收模板、V-03当前映射和V-04有效素材。明确性能标准来源；当前U-08依赖本包，需先明确其预算规格提供方式，再判AC3，不等待U-08整体DONE才能开始实施。
2. 实现：复用公共Prefab和四层扩展点，组装一个完整固定底图与独立RGBA素材的天气；不另写会话时钟或修改公共SceneAdapter。出口为可运行天气场景、参数及环境音频。
3. 联调：消费v2.2步骤与周期身份，同源开发fixture检查双条件、质量四态、暂停中止及累计锁定；ACK与真实render_receipt分别留证。抽象四天气推广归U-07，不把它作为U-03切片前置。
4. 验收：目标设备跑Play和Profiler，提交截图、参数、声音与模板漂移证据。按已明确预算核对，复核与真实签收按任务要求执行，交接U-07/U-08；合成输入不能替代真实设备或正式资格。

## 技能与资料

Unity、粒子、Shader、音频和Profiler。沿用[Unity中文学习](https://learn.unity.com/?locale=zh_CN)与[Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)，按本包步骤学习Prefab、粒子、材质、Audio Mixer及Profiler章节。工程版本来自ProjectVersion，不由教程版本决定。

## 当前入口

[天气B交接](outputs/current-adapter.md)、[实际来源](inputs/sources.json)、[复测入口](execution/verify.ps1)、[旧工具归档](archive/README.md)。当前验证覆盖规范化和旧菜单移出后的共享程序集，不表示天气B已经实现。
