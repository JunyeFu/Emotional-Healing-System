# 参与SRP开发

[开发上手](human/developers/README.md) · [任务领取与审阅](human/tasks/README.md) · [项目约束](https://github.com/JunyeFu/Emotional-Healing-System/blob/f2fefece8e55c10c93c737a8b69bbeaa37a65be9/AGENTS.md)

1. 先读项目概览与模块合同，再领取当前解锁任务；保留领取时输入快照，上游变化通过显式交接接收。
2. 在 `codex/<简短主题>` 分支完成单一范围改动。源码归 `agent/modules/`，任务工具归 `agent/tasks/<编号>/`，人类入口归 `human/`。
3. 按范围执行定向测试，记录命令、结果与未完成项。任务事实修改后用 `agent/tools/build_task_reviews.py` 刷新审阅材料。
4. 提交前查看差异，只暂存相关文件；不提交设备原始数据、凭据、缓存、本地环境和他人未提交候选。
5. 提交说明写明变化、验证与交接。业务状态变化必须同步治理注册表、分发包和进度图，不仅改README。

命名以[目录规范](human/project/repository-layout.md)为准；历史签收、冻结原件、Unity GUID和原生工程身份不能随整理改写。

默认main为展示与版本导航，完整实现保留在工作分支。展示只使用已有证据及明确标识的设计候选，不把静态验证写成参与者效果。
