# F-01 【合同与协议】运行合同v2与fixture

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex
- 分支：`codex/f-01-runtime-contract`
- 第二复核人：PENDING_SECOND_PERSON
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：合同与协议
- 波次：W0
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：无
- 所需技能：Python+JSON Schema+合同测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-SCHEMA Apifox JSON Schema中文教程](https://json-schema.apifox.cn/)
- [L-PYTEST pytest中文文档](https://pytest.cn/en/stable/)

## 交付物

- Schema
- manifest与消息fixture
- 迁移说明
- 合同测试

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1合法fixture全通过
- [ ] AC2缺字段错版本正式Mock和重复控制失败关闭
- [ ] AC3未知兼容字段被安全忽略

## 必需证据

- [ ] tests/contract报告
- [ ] fixture哈希
- [ ] 端口登记记录

## 完成条件

全部AC通过且第二人复核接口

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
