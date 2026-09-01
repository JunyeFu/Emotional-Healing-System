# T-01 【TouchDesigner】遥测设备质量与时钟面板

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：未领取
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：未指定
- 领取时间：未领取

## 任务边界

- 领域：TouchDesigner
- 波次：W1
- 状态：`READY`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：F-01、F-04、F-05
- 所需技能：TouchDesigner+UDP+DAT+CHOP
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-TD B站TouchDesigner零基础课程检索入口](https://search.bilibili.com/all?keyword=TouchDesigner%20%E9%9B%B6%E5%9F%BA%E7%A1%80)

## 交付物

- UDP5005客户端
- 20Hz节流
- 设备SQI延迟序号面板
- 断流状态

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1fixture重放字段正确
- [ ] AC2乱序丢包和断流显示正确
- [ ] AC3任何节点均不回写权威状态

## 必需证据

- [ ] fixture录像
- [ ] 节点导出
- [ ] 断流截图

## 完成条件

只读取F-01与F-05合同遥测

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
