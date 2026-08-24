---
status: accepted
---

# 通过不可变预发布分发大型预演制品

V-04完整MP4、WAV、ZIP、中间帧和FFmpeg二进制不进入普通Git，也不在本轮引入Git LFS。工作制品位于被Git忽略的`.artifacts-local/V-04/<candidate_id>/`；H3通过后按稳定规则拆为单个目标小于1.5 GiB、硬上限2 GiB的附件，并上传到绑定候选提交的GitHub `PRERELEASE`。普通Git只保存分镜源、轨迹、脚本、清单、缩略图和报告。独立复核与第二人审核同时绑定候选提交SHA和候选清单SHA；进入复核后的附件不得覆盖，任何变化都创建新候选身份和新预发布。
