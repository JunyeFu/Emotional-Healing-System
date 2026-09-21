# U-02 【Unity】四层SceneAdapter实现与降级

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex(Grip)/小彬
- 分支：`codex/u-02-grip`
- 第二复核人：独立Agent复核；真实第二人签收另记
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：Unity
- 波次：W1
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：F-03、F-05、V-03
- 所需技能：Unity+C#+接口实现+测试
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)

## 交付物

- SceneAdapter
- Target Actual Recovery Fallback四层
- 锁定
- 重置
- 降级

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [x] AC1每层单独变化不影响其他层且实现符合V-03映射合同
- [x] AC2锁定后累计状态不再变化且重置只在合法生命周期发生
- [x] AC3降级不伪造成功也不从背景动画泄露目标节律

## 必需证据

- [x] 接口测试
- [x] 参数快照
- [x] 层级隔离测试
- [x] 降级录像

## 完成条件

全部天气和抽象条件只能通过同一SceneAdapter扩展点接入且正式模式消费已签收F-05合同

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PENDING`
- 证据路径：`03-测试与实验/F-03_技术验收记录_已签署.md`；`00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/20_产品与场景设计/V-03_四层视听映射与资产来源基线/V-03_技术验收记录_已签署.md`
- commit：`9078bc19f1efa2a512e2bb4992568c869fa895b2`
- push目标：`origin/codex/u-02-grip`
- 真实团队第二人复核：`PENDING`
- 剩余风险：傅钧烨签收仍开放；任务文档列明的外部边界仍开放
