# P-01 【Python核心】manifest与会话编排

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：未领取
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：未指定
- 领取时间：未领取

## 任务边界

- 领域：Python核心
- 波次：W1
- 状态：`READY`
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：F-01
- 所需技能：Python+状态机+性质测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-PY Python官方中文教程](https://docs.python.org/zh-cn/3/tutorial/)
- [L-PYTEST pytest中文文档](https://pytest.cn/en/stable/)

## 交付物

- SessionCore
- manifest校验
- 段模块状态机
- 幂等控制
- 正式失败关闭

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1确定性时钟测试通过
- [ ] AC2重复事件不重复推进
- [ ] AC3非法转换性质测试与四模块加速回放通过

## 必需证据

- [ ] pytest报告
- [ ] 状态轨迹
- [ ] 接口说明

## 完成条件

SessionCore只依赖合同不导入Unity或TD

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
