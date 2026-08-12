# F-03 【Unity】会话运行壳

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：未领取
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：未指定
- 领取时间：未领取

## 任务边界

- 领域：Unity
- 波次：W0
- 状态：`READY`
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：无
- 所需技能：Unity+C#+状态机+Play Mode
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)

## 交付物

- Python控制驱动的渲染镜像状态机
- 25/150/25配置
- 自动转场
- 正式开发标记
- 无TD启动

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1合法非法渲染镜像转换测试通过
- [ ] AC2消费P-01 golden轨迹完成四模块
- [ ] AC3正式模式缺manifest失败关闭且无TD仍完成

## 必需证据

- [ ] Unity测试XML
- [ ] 运行录像
- [ ] 构建日志

## 完成条件

渲染镜像状态和无TD路径可复现且不成为研究流程权威

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
