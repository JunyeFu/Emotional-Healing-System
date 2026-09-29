# U-01 当前可靠控制使用说明

## 状态与范围

U-01注册表为DONE，傅钧烨于2026-09-07签收候选6c09f71d14bcb0288a4b83f87b177975c49bfe3d。历史报告写IN_REVIEW是审阅对象原状态，非当前待签收。当前实现提供可靠控制探针，不代表完整参与者制品。

## 权威与消费

- P-01唯一负责会话、顺序与单调时间；Unity帧、ACK和本地Stopwatch不推进研究流程。
- SessionMirror消费prepare/start/pause/abort/end/module/segment，只维护只读镜像。start兼作恢复；不新增resume命令。
- U01RuntimeBridge默认v2.2、TCP 127.0.0.1:5010、UDP 127.0.0.1:5006；v2.1仅dev_replay。F-05已签收，步骤实例直接读取合同字段，不从phase或progress推断。
- ACK说明控制已应用或拒绝，不说明画面已呈现。适配器完成对应帧后显式调用ConfirmRendered(event_id, frame_seq)，生成的回执才进入发送路径。
- ConfirmRendered返回true表示确认已生成；发送失败仍由LastFailure表示。已确认回执保存事件身份并在重连或同ID重发时再次发送，Python幂等消费，P-02保存实际输入消息。
- TD缺席不改变此组件，但最终脱离TD制品仍须由构建/装配任务验证。

## 当前执行

在D:/Agent/srp运行：

```powershell
py -3.14 agent/tasks/U-01/execution/verify.py
```

或execution/verify.ps1。主机验证器verify_u01.py已从历史evidence迁出，默认校验本包evidence/runtime；--evidence-dir可只读检查历史证据。

verify.py使用D:/UnityEngine/6000.4.9f1/Editor/Unity.exe，顺序运行14项EditMode、3项PlayMode、SRP.U01.Editor.U01EvidenceBuilder.Generate和新旧证据校验。Unity工程不能同时被另一个Editor进程占用。新结果不写历史签收目录。

Editor生成器必须位于Assets/U01/Editor以保持程序集关系；根目录19/19项已迁入human/agent，当前读取和运行入口已验证，业务签收不变。

## 上下游交接

19控制、19ACK、12回执是明确标记的contract_golden_fixture，由编辑器调用镜像和显式确认构造。它们验证合同消费，不是完整场景真实呈现的录像或真实设备回执。

U-02/U-03负责接入四层渲染与呈现确认；I-01验证真实全链，正式构建另验资产与准入。P-02不根据golden推测实际已呈现。核心前分条件教学尚待U12-11冻结和P-01暴露登记接入；本组件不创造教学事件或扩大正式门资格。

当前使用说明与历史记录分开，保留真实签署、原XML和JSON。规范化不改变注册状态，也不追加真人签收。
