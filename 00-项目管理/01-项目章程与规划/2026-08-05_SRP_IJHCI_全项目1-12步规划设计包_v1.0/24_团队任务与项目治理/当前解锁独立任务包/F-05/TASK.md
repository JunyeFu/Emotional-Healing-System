# F-05 【合同与协议】相位实例v2.2与消费者迁移

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex Agent（F-05独立对话）
- 分支：`codex/f-05-phase-v22`
- 第二复核人：傅钧烨（团队总监，独立第二人复核人）
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：合同与协议
- 波次：W1
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：F-01、P-01、P-02
- 所需技能：Python+JSON Schema+兼容迁移+合同测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-SCHEMA Apifox JSON Schema中文教程](https://json-schema.apifox.cn/)
- [L-PYTEST pytest中文文档](https://pytest.cn/en/stable/)

## 交付物

- 不可变v2.1与版本化v2.2 Schema
- storm双停与fade双吸步骤fixture
- 消费者迁移指南
- P-01与P-02适配
- Unity与TD消费合同fixture
- 专项验证器

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [x] AC1v2.2显式提供周期步骤与实例标识并无损表达storm两个停留和fade两次吸气且v2.1保持不可变
- [x] AC2合法非法重连暂停重复输入和确定性重放合同测试通过
- [x] AC3未迁移消费者在正式模式失败关闭且不得从相位名称或进度猜测步骤实例

## 必需证据

- [x] Schema与fixture哈希
- [x] 合同测试报告
- [x] 消费者迁移矩阵
- [x] 独立复核记录
- [x] 第二人签收报告

## 完成条件

v2.2及全部正式消费者迁移经第二人签收后才允许U-01 U-02 T-01和U-07进入实现

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PASS_FOR_MODEL_INDEPENDENT_REVIEW`
- 证据路径：`03-测试与实验/evidence/F-05/evidence_manifest.json`；`03-测试与实验/evidence/F-05/evidence_hashes.sha256`
- commit：`c7c760b83289e7e15c8c1ab65ca52470305cd0dc`
- push目标：`origin/codex/f-05-phase-v22`
- 剩余风险：真实团队第二人签署及任务文档列明的外部边界仍开放
