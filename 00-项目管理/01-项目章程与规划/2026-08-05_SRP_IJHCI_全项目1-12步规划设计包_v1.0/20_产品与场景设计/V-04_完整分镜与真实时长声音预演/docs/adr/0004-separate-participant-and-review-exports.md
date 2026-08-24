---
status: accepted
---

# 分离参与者视图与评审视图

V-04输出`scene_native`和`abstract_pacer`两种条件各自的带声、静音完整参与者视图，共4条视频；另输出1条左右并列的双条件评审视图。条件名、统一时间码、画面节拍、输入状态和差异标记仅允许出现在标记为`REVIEW_OVERLAY_NOT_PARTICIPANT_VISIBLE`的评审边框，不能进入或缩放参与者实际可见画面；评审视频只使用一条共享声音轨。
