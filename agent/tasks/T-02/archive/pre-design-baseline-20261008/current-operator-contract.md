# T-02 当前请求与操作台交接

T-02仍READY且无人领取；人工标记、中止请求、告警和审计视图均没有完整实现，不存在本包真人签署。已有T-01/P-01/P-02签收不扩大到这些功能。

## 可消费的实际接口

- T-01读取5005遥测并保留不可变快照、本地计数和步骤身份。当前v2.2与研究v1.2分别指运行消息及研究设计，不能混用版本。
- P-01 TCP5010支持transport_version 1.0和TD角色握手，但全部TD消息仍返回TD_STATE_CHANGE_NOT_AVAILABLE；握手接受不等于请求已开通。
- OperatorRequest(request_id, action, reason_code)是Python内部类型，既不是F-01消息，也不是已经冻结的TD JSON请求。核心只接受start、pause、abort；人工标记不能调用manual_mark推进核心。
- SessionRuntimeHost串行处理核心操作并交付Unity。RecordingSessionCore先耐久记录操作和结果，再允许控制发送；T-02必须沿同一代理和主机，不绕回裸SessionCore。
- P-02 SessionArchive.append_l1可记录非空record_type的隐私合规payload，但“允许追加”不等于人工标记服务已完成。标记handler、格式、请求ACK及TD消费者均缺。

## 实施与验收边界

仅向Python请求mark/abort，Python是判断和记录权威。mark写L1而不转换核心状态；abort消费核心内部动作并由主机送Unity。请求ACK与Unity控制ACK/渲染回执必须分开：Python拒绝、接受、耐久记录和实际控制交付各显示实际事实。socket发送成功不能显示已中止。

告警列表可消费T-01断流、无效帧与fallback；已读确认不能修改阈值、质量、顺序、会话或Unity。TD缺席不影响独立体验。实际告警历史/确认、请求身份关联、重连后的状态展示、耐久审计与操作录像仍待本包交付。

用户要求的A主题可读性与原生控件由后续实际TD验证完成；UI13至UI16是本包核心。UI17至UI20分别为快照、截图、归档与事件导出扩展，待单独实现及验收。完整会话导出须通过Python及G-02权限；不由TD读取受限原件，不把快照或手动标注冒充设备数据。

## 本轮已整理

15份旧TD引导/遥控资料和工程原件迁入archive/legacy-td-authoring；它们使用旧scores字段、默认补零、TD参与者引导与任意代码执行，不能作为当前请求协议。保留历史字节及内部相对关系；原文说明入口改为当前导航。T-01/F-04制品、签署、共享Python代码及mcp_td_v147开发工具未改。

READY分发包更新为研究v1.2并补本页、机器现状、P-02与实际Python接口输入。IN_PROGRESS/IN_REVIEW冻结输入不改；业务状态、负责人及任务图不变。后续A-01消费运行记录时必须区分设备原始数据、人工标记、在线事实和离线重算。
