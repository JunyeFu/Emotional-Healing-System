# Python在线与离线模块设计

## 在线模块

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
