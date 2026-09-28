# U-03 最高风险天气纵向切片与模板冻结

## 状态与责任

注册表WAIT_DEP，依赖U-01、U-02、V-05，约5人日，process_profile为P-DEV。领取人、分支、复核人均为空。V-05尚未通过；本轮规范化不代为领取，不解锁或签收实际切片。

## 对象与验收

V-03历史七维双评分及差异裁定选定fade，不能默认复用旧storm。原评分是设计判断，不是当前固定镜头方案的性能实测。

- AC1按V-03的选择完成fade，而非以现有场景文件证明切片。
- AC2完整模块内同时具备Target、Actual、Recovery、Fallback、环境声音和真实渲染回执，不需参与者操作。U-03同时实现最小完整abstract_pacer对照，U-07推广其余天气。
- AC3形成性问题关闭，冻结Prefab、图层、音频总线、生命周期、性能及证据模板后才向U-04至U-07放行。

必需证据为Play录像、控制与渲染回执序列、形成性问题关闭表、Profiler报告、模板冻结哈希及截图组。参数候选与Python测试不能替代这些证据。

## 五天过程与出口

1. 等待V-05实际验收，核对当前V-03/V-04、U-01/U-02和F-05；明确真实负责人及工程输入版本。出口为足够使用的输入和切片范围。
2. 在共享Unity工程组装固定镜头fade及双条件最小场景。完整底图配独立RGBA素材，不拆层、不横向滚动，不引入TD/Spout运行依赖。出口为可运行的双条件画面。
3. 接入v2.2步骤身份及四层只读视图。双吸长呼为inhale_1 2.5秒、inhale_2 1.5秒、exhale_1 6秒；第二吸不回零，Actual不复制Target或补造第二吸。整屏复色由模块有效时间驱动，两条件同曲线，Recovery仅改变独立轮廓和纹理。出口为分层负测及阶段可辨识画面。
4. 接入P-01控制及U-01 ConfirmRendered，在真实呈现后回执；运行完整模块、暂停恢复、中止和四种质量状态，采集Profiler与录制。出口为画面、控制、回执和记录可对应的证据。
5. 真实形成性审阅并关闭问题；再冻结公共模板、候选降级可见参数、声音和性能预算，交接U-04至U-08。出口为真实复核及按项目流程签收的模板；不把规划文件作为模板已冻结。

## 技能与资料

必需Unity、粒子、Shader、音频、Profiler和模板化。国内教学沿用[Unity中文学习入口](https://learn.unity.com/?locale=zh_CN)和[Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)，重点学习Prefab、粒子、材质、Audio Mixer及Profiler章节。资料版本不代替ProjectVersion中的工程版本；不为本轮整理新增工具依赖。

## 执行与交接

[当前切片交接](outputs/current-slice.md)、[来源索引](inputs/sources.json)、[验证入口](execution/verify.ps1)。共享实现仍属Unity模块，本包不复制工程或缓存；旧场景设计已归archive，仅供迁移理解。
