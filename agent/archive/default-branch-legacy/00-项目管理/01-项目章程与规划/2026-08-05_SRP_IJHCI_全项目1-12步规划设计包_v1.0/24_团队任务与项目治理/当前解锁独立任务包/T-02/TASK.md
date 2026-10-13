# T-02 【TouchDesigner】人工标记中止请求与告警

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：未领取
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：未指定
- 领取时间：未领取

## 任务边界

- 领域：TouchDesigner
- 波次：W2
- 状态：`READY`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：T-01、P-01
- 所需技能：TouchDesigner+请求协议+权限负测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-TD B站TouchDesigner零基础课程检索入口](https://search.bilibili.com/all?keyword=TouchDesigner%20%E9%9B%B6%E5%9F%BA%E7%A1%80)
- [L-SCHEMA Apifox JSON Schema中文教程](https://json-schema.apifox.cn/)

## 交付物

- 人工标记
- 中止请求
- 告警
- 审计视图

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1请求只发送Python
- [ ] AC2每次请求有ACK和审计记录
- [ ] AC3直接控制Unity和修改阈值的负测试失败

## 必需证据

- [ ] 请求日志
- [ ] 权限负测试
- [ ] 操作录像

## 完成条件

不成为会话状态权威

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
