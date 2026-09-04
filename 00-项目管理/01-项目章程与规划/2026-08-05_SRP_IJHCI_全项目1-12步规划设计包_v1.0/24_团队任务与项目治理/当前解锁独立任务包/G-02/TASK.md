# G-02 【数据治理】数据分级跨阶段去重与资产许可

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex
- 分支：`codex/g-02-data-governance`
- 第二复核人：傅钧烨（团队总监，独立第二人复核）
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：数据治理
- 波次：W1
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：4人日
- 前置依赖：F-01
- 所需技能：数据治理+最小权限+资产许可
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-DATASEC 阿里云开发者社区数据安全课程检索入口](https://developer.aliyun.com/search?q=%E6%95%B0%E6%8D%AE%E5%AE%89%E5%85%A8)
- [L-GIT 廖雪峰Git教程](https://www.liaoxuefeng.com/wiki/896043488029600)

## 交付物

- L0至L5分级
- 机构密钥控制的HMAC联络去重表
- 密钥与数据物理分离
- 研究ID映射隔离
- 跨阶段重复审计
- 权限矩阵
- 备份恢复
- Unity音视频字体许可台账

## 四阶段过程

1. 核对冻结依据、构念、权限和不承担项。
2. 形成候选材料、配置或治理台账。
3. 用双人审查、合成样例或检查表迭代。
4. 冻结版本、记录差异并向下游交接。

## 验收要求

- [x] AC1HMAC去重表密钥与研究manifest物理分离且manifest不含联络信息
- [x] AC2跨Level B/C阶段一三重复审计和最小权限恢复演练通过
- [x] AC3所有发布资产有许可或替换计划

## 必需证据

- [x] 权限负测试
- [x] 重复审计fixture
- [x] 恢复演练日志
- [x] 资产许可台账

## 完成条件

数据去重和资产规则被X-01/Z-01/W-03消费

完成还必须满足：任务文档列明的外部与下游门禁关闭。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PASS_FOR_MODEL_INDEPENDENT_REVIEW`
- 证据路径：`02-技术研发/05-通信协议/F-01_技术验收记录.md`；`02-技术研发/07-数据治理/G-02_技术验收记录.md`；`02-技术研发/07-数据治理/evidence/asset_scan_report.json`；`02-技术研发/07-数据治理/evidence/formal_environment_report.json`；`02-技术研发/07-数据治理/evidence/repository_privacy_report.json`；`02-技术研发/07-数据治理/evidence/synthetic_rehearsal_report.json`；`02-技术研发/07-数据治理/evidence/unity_formal_build_gate_summary.json`
- commit：`03d7426219121e49554e405db9dd521b8ab1d819`
- push目标：`origin/codex/g-02-data-governance`
- 真实团队第二人复核：`PASS`（签收提交`ea132c8f26db76d1a1f97daebea5e97258d969c4`）
- 剩余风险：正式专机配置、机构保留期限批准、Unity资产许可门与X-01/Z-01/W-03下游消费仍开放
