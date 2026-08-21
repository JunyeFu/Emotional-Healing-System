# P-02 【数据记录】L0/L1追加记录与重放

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex
- 分支：`codex/p-02-session-store`
- 第二复核人：待真实团队第二人复核
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：数据记录
- 波次：W1
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：F-01
- 所需技能：Python+追加日志+校验和+重放
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-PY Python官方中文教程](https://docs.python.org/zh-cn/3/tutorial/)
- [L-PYTEST pytest中文文档](https://pytest.cn/en/stable/)

## 交付物

- L0原始包
- L1事件ACK回执
- manifest与哈希
- 重放读取器

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [x] AC1中断恢复不覆盖旧数据
- [x] AC2校验和发现改写
- [x] AC3相同输入重放产生相同状态事件

## 必需证据

- [x] 恢复测试
- [x] 篡改负测试
- [x] 重放哈希报告

## 完成条件

L0/L1格式被A-01和设备适配器消费

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PASS_FOR_MODEL_INDEPENDENT_REVIEW`
- 证据路径：`02-技术研发/05-通信协议/F-01_技术验收记录.md`；`02-技术研发/srp_session_core/fixtures/golden/four-module-trace-v1.json`；`02-技术研发/srp_session_store/P-02_技术验收记录.md`；`02-技术研发/srp_session_store/evidence/synthetic_stress_report.json`；`02-技术研发/srp_session_store/fixtures/golden/session-archive-v1/evidence.json`
- commit：`03d7426219121e49554e405db9dd521b8ab1d819`
- push目标：`origin/codex/p-02-session-store`
- 剩余风险：真实团队第二人签署及任务文档列明的外部边界仍开放
