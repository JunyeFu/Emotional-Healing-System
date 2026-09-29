---
status: accepted
date: 2026-08-23
---

# 四级后台质量折叠为两类可见降级

Python继续记录`GOOD/DEGRADED/UNUSABLE/DISCONNECTED`四级质量状态，参与者界面只呈现“低确定性”和“暂不可用”两类降级语义。`DEGRADED`使实际反馈保持运动但变得断续和柔化；`UNUSABLE/DISCONNECTED`停止实际相位推进并保留静态断续轮廓。目标按Python裁定开环继续或中止，累计在不可用和断连时暂停并锁定最后值；不增加文字、提示音、全屏警告或技术原因说明。
