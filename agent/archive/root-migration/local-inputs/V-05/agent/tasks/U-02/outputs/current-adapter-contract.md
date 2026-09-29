# U-02 当前四层适配与降级说明

## 范围与权威

原任务DONE，真实签收仅覆盖原候选。当前补丁另行记录，不把旧签名转移。Runtime位于Assets/Scripts/V03，Target/Actual/Recovery/Fallback通过独立只读投影应用；BackgroundPass只有段换场钩子，不持有呼吸节律。

P-01拥有顺序、时间与会话权威。U-01网络入口校验外部合同、会话身份和陈旧帧；V03FrameValidator负责本包投影语义，不替代完整F-05网络门。真实IV03TelemetrySource接入及渲染确认仍由下游装配。降级接口NotifyLinkDown不构造成功帧、不推进研究流程。

## 本轮契约修复

- Recovery在同模块保持锁定，包括closed_loop到lock_transition；只有SessionId、ModuleId或ModulePosition变化才开始新累计生命周期。背景段钩子独立执行，不与累计重置混用。
- 四天气phase=none、progress=0、cycle/step均null为合法空步骤；有相位却无实例仍拒绝。v2.2版本与缺字段检查留在网络边界，不以模块名排斥合同合法空状态。
- DevTools驱动整体以UNITY_EDITOR或DEVELOPMENT_BUILD条件编译；非开发Player不包含StubSource。Editor构建器通过F03BuildAuthorization.Begin申请受控开发构建，退出恢复原环境与四项屏幕设置；正式门不放宽。
- 演示通过Camera.targetTexture和RenderPipeline.StandardRequest显式渲染只读状态面板，ReadPixels读取实际离屏纹理，避免隐藏窗口屏幕截图和自动渲染的黑帧；保存成功才增加计数。主机对120帧逐一检查尺寸、像素极差和标准差，再由人工检查五阶段文字与状态；ffprobe验证编码后的120帧。

## 当前命令与证据

在D:/Agent/srp执行py -3.14 agent/tasks/U-02/execution/verify.py，或verify.ps1。105项EditMode中88项为U-02专项、17项为F-03/U-01联测；另3项PlayMode为U-01。参数输入采用既有规范化UTF-8/LF哈希，不能把Windows CRLF字节差异当设计变化。

generate_demo.ps1消费本机Unity 6000.4.9f1及.tools/ffmpeg/9.0.1。新素材在evidence/runtime/demo；开发EXE只在.artifacts-local。历史127文件在archive/evidence-v1保持Git提交原字节；旧视频不代表本轮补丁后的运行。

截图依据[Unity 6.4 RenderTexture](https://docs.unity3d.com/6000.4/Documentation/ScriptReference/RenderTexture.html)、[ReadPixels](https://docs.unity3d.com/6000.4/Documentation/ScriptReference/Texture2D.ReadPixels.html)及[URP显式渲染请求](https://docs.unity3d.com/cn/6000.0/Manual/urp/User-Render-Requests.html)，读取的是Unity实际UI渲染，不是主机重绘的替代图。

## 交接与未完成范围

本包只有逻辑参数与技术演示，不是四天气最终渲染。V-04当前固定镜头及美术机制由V-05/U-03接入；旧参数候选不自动等于最终天气视觉。U-01的ConfirmRendered需要适配器实际完成对应帧；本包没有伪造该联调已完成。

真实设备链、完整800秒旅程、两条件体验匹配、正式构建与研究准入继续由各自下游验收。新代码由独立Agent复核后保留待补丁真人审阅，不新增或代填傅钧烨签收。
