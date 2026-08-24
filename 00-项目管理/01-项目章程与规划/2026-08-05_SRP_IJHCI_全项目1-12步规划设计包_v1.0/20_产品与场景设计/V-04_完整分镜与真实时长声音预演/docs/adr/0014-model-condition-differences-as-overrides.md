---
status: accepted
---

# 将条件差异建模为覆盖字段

V-04每个画面节拍只建立一条共享记录，统一时间、事件、背景、卷轴、累计、声音、质量、转场和证据；`scene_native_override`与`abstract_pacer_override`只描述目标和实际表示载体。每条记录同时给出`expected_difference_mask`，掩码外任何背景、累计、声音、时长、事件、质量、转场或结束差异均判定为失败，以结构化方式阻止两条件漂移成两套体验。
