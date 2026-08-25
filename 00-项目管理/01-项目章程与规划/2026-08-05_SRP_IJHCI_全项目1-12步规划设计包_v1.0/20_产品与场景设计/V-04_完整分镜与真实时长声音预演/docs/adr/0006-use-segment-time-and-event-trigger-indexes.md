---
status: accepted
---

# 同时使用段时间与事件触发索引

V-04分镜以配置时间固定`demo`、`closed_loop`和`lock_transition`边界，同时以`target_cycle_index`、相位步骤、`recovery_value`和锁定事件触发内部画面节拍。参考轨迹可给出会话与模块相对秒数用于定位，但实现不得依据该参考秒数重置呼吸周期、强制相位结束或改变段边界。
