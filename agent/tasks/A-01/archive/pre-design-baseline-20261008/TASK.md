# A-01【离线分析】L0至L3确定性重建

状态 WAIT_DEP；依赖 P-02（DONE，范围受限）与 S-02（WAIT_DEP，算法未交付）。约5人日，P-ANALYSIS。负责人、分支及复核人未领取；不将本轮规范化登记为业务实现或签收。

## 目标与验收

读取不可覆盖原始证据，重建同步L1、事件L2和模块/参与者L3，交给A-02/A-03。范围不含改变会话状态、重复暴露、统计结果择优筛选或L4/L5最终模型。

- AC1 固定fixture逐层结果哈希稳定，记录版本和输入身份。
- AC2 在线事实与离线重算差报告自动生成，边界、缺失和匹配不到的记录明确列出。
- AC3 所有排除都有原因码；技术不可观测、执行不符合和量表缺失分开。
- 证据为pytest报告、层级manifest、差异报告、哈希清单和下游读取入口；目前未交付以上完整流水线。

## 五天推进

1. 核对六类RawEvidenceBundle、授权原件和P-02封存；冻结字段与fixture，缺必需输入先报告，不猜测。
2. 接入设备解码、S-01时钟与SQI；在offline_derived/L1写派生同步序列，保留在线事实。
3. 接入S-02实际事件与独立标注；按目标步骤生成机会L2，明确部分周期、暂停及不可观测原因。
4. 生成L3汇总、逐层manifest和在线/离线差报告；让A-02/A-03通过公开入口消费。
5. 重跑固定fixture、篡改/缺失负例和消费者测试，整理证据，再独立复核及真实签收。

每步须有实际产物与检查结果；只有计划和接口测试不能通过本包验收。

## 技能和资料

- Python文件与结构化数据：[廖雪峰Python教程](https://liaoxuefeng.com/books/python/introduction/index.html)，文件读写和JSON部分；用于受限原件读取及manifest。
- pandas表格对齐：[菜鸟pandas教程](https://www.runoob.com/pandas/pandas-tutorial.html)，合并、缺失值、分组章节；先掌握时间键对齐，不自行补齐缺失生理值。
- 测试：[pytest官方入门](https://docs.pytest.org/en/stable/getting-started.html)；用于固定输入、重复运行及负例。国内资料用于上手，实际接口以本库P-02和合同源码为准。

## 文件与责任交接

inputs保存必要来源与原件迁移记录，execution保存核验入口，evidence保存真实结果，outputs保存当前交接与总结，archive保留有理由的旧规则。共享存储实现仍在原模块，整体根迁移后再统一修引用。

当前消费顺序与未完成项见[重建交接](outputs/current-rebuild.md)。S-02算法、真实数据权限和实际责任人仍需落实；A-02/U12-04负责分析集与缺失模型，A-03冻结输入不刷新。
