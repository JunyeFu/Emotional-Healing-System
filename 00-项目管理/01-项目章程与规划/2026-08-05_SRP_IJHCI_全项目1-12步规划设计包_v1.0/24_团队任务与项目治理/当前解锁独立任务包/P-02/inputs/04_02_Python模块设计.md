# Python在线与离线模块设计

## 在线模块

- `srp_session_core.SessionCore`：manifest门、模块/段状态机、单调时间、幂等请求与控制序号；
- `srp_session_core.FixedSequenceProvider`：只消费已经生成的固定顺序和`PolicyDecision`；
- `srp_session_core.ControlServer`：TCP 5010 JSON Lines握手、ACK、同ID重发和重连；
- `srp_session_core.TelemetryPublisher`：校验完整v2.1帧与核心快照一致后镜像到UDP 5005/5006；
- `device_adapter`
- `clock_service`
- `raw_writer`
- `signal_quality`
- `resp_event_detector`
- `protocol_scheduler`
- `feedback_engine`
- `recovery_accumulator`
- `session_orchestrator`
- `event_logger`
- `randomization_loader`
- `qc_builder`

## 离线模块

- `ingest`
- `synchronize`
- `artifact_detection`
- `resp_event_rebuild`
- `manual_annotation_merge`
- `cycle_builder`
- `module_summary`
- `questionnaire_scoring`
- `analysis_set_builder`
- `model_runner`
- `figure_builder`
- `dataset_release`

## 原则

- 在线与离线使用同一事件定义；
- 离线可重建在线派生结果；
- 原始数据只追加；
- 算法版本写入每个派生文件；
- 正式阈值不从结果方向反推。
- Unity只维护渲染镜像，TouchDesigner只读；两者都不能推进`SessionCore`状态。
- v2.1只支持预先确定的完整天气顺序；阶段三冻结策略在v2.2合同完成前返回`ADAPTIVE_SEQUENCE_REQUIRES_V2_2`。
- 默认P-01依赖只允许合成回放；P-02候选未签收或未正式装配、X-01和G-02正式门未接入时，`formal_*`失败关闭。
