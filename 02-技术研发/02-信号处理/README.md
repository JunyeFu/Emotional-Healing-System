# 交互状态估计模块

当前S-02执行入口为[事件与在线PF交接](../../agent/tasks/S-02/outputs/current-events.md)。任务仍WAIT_DEP；没有真实四结构事件检测、步骤实例识别、在线PF及双人标注验收结果。

`signal_pipeline.py`、`scoring_model.py`、`dimension_spec.py`及相应测试仍服务旧v1.2开发入口，不是F-01/F-05正式实现。旧模型的四维评分、EDA必需输入、标量呼吸缓冲和calm_index不能替代当前两设备原生数据、实际事件或机会PF。`score(None)`的中性帧仅是旧API行为，正式链不得用它补齐缺失；main.py已在处理结果为空时跳过发送。

旧评分设计已实际归入[历史归档](../../agent/tasks/S-02/archive/评分模型设计.md)。A-03已领取输入副本保持冻结，迁移影响见[消费者影响记录](../../agent/tasks/S-02/evidence/consumer-impact.md)。

`a03_gate2_spec/`继续保持所属研究任务的实现和验收范围；其中阶段错误率不是S-02的机会PF。当前研究由PANAS主要结果、独立功能护栏和SCCI操纵检查组成，不沿用旧有序门限制预设情绪结果报告。
