# T-02 【TouchDesigner】人工标记中止请求与告警

## 当前结论

注册表为READY、未领取、约3人日，前置T-01和P-01已完成其限定范围。本轮仅完成双层规范化、旧材料归档、接口现状复测与交接，不将T-02改为IN_REVIEW或DONE，不代填真人负责人。

人读总结为`human/tasks/T-02/summary.docx`；当前执行依据为本工作单和`outputs/current-operator-contract.md/.json`，不是旧OSC控制器，也不是T-01禁用按钮。

## 目标与边界

交付人工标记、中止请求、告警与审计视图。AC1请求只发送Python；AC2每次请求有请求ACK和审计记录；AC3直接控制Unity及修改阈值的负测试必须拒绝。必需请求日志、权限负测试和实际TD操作录像，第二人复核后按项目流程签收。

Python仍拥有核心会话、单调时间、天气顺序、交互状态估计与控制序号。TD可以请求，但不能自行改变Unity镜像或Python状态。告警确认只改变本地已读状态，不把质量改为GOOD、不修改SQI阈值，也不中止或恢复会话。

当前TCP5010接受TD握手后，对TD消息统一返回TD_STATE_CHANGE_NOT_AVAILABLE。SessionCore内部OperatorRequest只有start、pause、abort；没有manual_mark、resume或end动作。T-02不应把start/pause作为任意远程控制暴露。mark需由Python记录服务消费而非伪装成核心转换；具体请求与响应格式仍需实施时冻结。

## 统一目录

- inputs：权威文件路径和采用版本，不复制共享模块或受限原件。
- execution：本轮核验脚本及定向测试；共享TD/Python源码暂留原模块，最终整体迁移。
- evidence：真实运行输出、消费者影响与验证范围。
- outputs：当前接口现状、结构化总结；Word只能从此层生成。
- archive：失效TD呼吸引导、任意脚本遥控和旧工程原件，禁止作为当前入口执行。

## 三天实施过程

1. 对齐：读取T-01只读基线、F-05 v2.2、P-01 ControlServer与P-02 RecordingSessionCore；明确人工标记、请求ACK、审计行与Unity ACK的不同身份。冻结最小请求协议和权限用例，不修改F-01/F-05现有消息以假装已有支持。
2. 实现：TD只提交人工标记和中止请求；Python串行接收、验证、记录和回答。中止通过同一RecordingSessionCore及SessionRuntimeHost；人工标记只写耐久L1。界面展示待响应、Python接受/拒绝、持久化结果及真实Unity交付结果，不能以按钮点击或socket发送成功冒充完成。
3. 验证与交接：运行正常、重复、非法动作、错误会话、存储失败、断连与权限用例；TD实际录像覆盖告警确认、标记、拒绝和中止。核对P-02离线消费及A主题可读性，提交独立复核和真实签收。

实际领取人和第二复核人由领取流程登记；公共Python接口指定唯一集成人，不能由规范化Agent虚构分派。

## 必须补齐的验收

| 项目 | 当前事实 | T-02交付要求 |
|---|---|---|
| AC1请求路由 | TD请求仍禁用，5010仅保留角色入口 | 只到Python；不新增TD直连Unity或控制UDP |
| AC2请求与审计 | P-01内部审计和P-02耐久代理可用，但无TD请求ACK | 真实请求、Python回应、耐久审计可关联；UnityACK独立显示 |
| AC3权限负例 | 现有TD入口统一拒绝，尚无正向请求能力 | 正向mark/abort可用后，直控Unity、调阈值、改顺序仍拒绝 |
| 告警 | T-01有断流、无效帧及降级来源，无完整告警历史/确认 | 状态与告警已读分开；不把本机帧龄当设备到屏幕延迟 |
| 实际操作证据 | 禁用控件和旧TOE不是T-02录像 | 可打开的TD操作录像、请求日志及复核记录 |

## 与用户工作台要求的关系

A主题的UI13至UI16属于本包核心。UI17快照导出、UI18截图、UI19完整会话导出、UI20事件导出是已提出的后续功能，不以本包基础AC替代其验收；需要分别定义输出、权限和结果。导出不能向TD复制受限L0原件或把当前快照称为完整会话。当前不实现这些扩展，也不把它们写成已交付。

## 学习资料

- [国内TouchDesigner入门视频检索](https://search.bilibili.com/all?keyword=TouchDesigner%20Panel%20Execute%20DAT)：定位原生Button COMP、Panel Execute DAT与事件回调课程。
- [Apifox JSON Schema中文资料](https://json-schema.apifox.cn/)：为本包请求、响应和拒绝示例定义字段。
- 原生控件与TCP运行事实优先按任务包采用的TD版本官方资料复核；本轮没有新增控件或引用未经查证的接口行为。

## 本轮核验入口

在项目根运行`py -3.14 agent/tasks/T-02/execution/verify.py`。核验现有P-01/P-02及T-01/F-04、实际本机TCP拒绝、旧材料完整性和当前交接。没有启动TD或Unity，不证明真实设备或T-02业务完成。

下一规范化包A-01；业务状态和任务图不因本轮整理而改变。
