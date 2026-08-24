---
status: accepted
---

# 用一条配对评审卷覆盖失败状态

V-04为四个天气各制作`GOOD → DEGRADED → GOOD`和`GOOD → TEMPORARILY_UNAVAILABLE → GOOD`两个双条件配对片段，共8段，并追加1段统一平稳中止预览后串成一条约2分钟评审卷。暂时不可用片段在评审边框依次标记`UNUSABLE`和`DISCONNECTED`，但原因码切换时参与者画面必须不变；全部片段不进入800秒主视频，不新增文字、告警音、红色警示或技术原因。
