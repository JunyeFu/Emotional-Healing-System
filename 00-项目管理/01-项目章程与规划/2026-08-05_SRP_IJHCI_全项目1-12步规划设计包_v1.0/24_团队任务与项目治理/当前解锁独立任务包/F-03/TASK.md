# F-03 【Unity】实验环境基线与会话运行壳

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
- 预计工作量：5人日
- 前置依赖：无
- 所需技能：Unity+C#+状态机+Play Mode+环境复现+构建
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)

## 交付物

- 精确Unity与包锁环境报告
- 基线编译和测试架
- Python控制驱动的渲染镜像状态机
- 25/150/25配置
- 自动转场
- DEV-REPLAY标记
- 无TD无Spout开发构建
- 资产阻断清单

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1精确Unity和包锁可在干净工作区恢复并编译且漂移失败关闭
- [ ] AC2消费P-01 golden轨迹完成四模块各一次且非法转换重复控制不推进
- [ ] AC3无TD无Spout开发构建完成入口四模块结束且正式模式缺manifest或资产门失败关闭

## 必需证据

- [ ] Unity环境报告
- [ ] 包锁哈希
- [ ] 测试XML
- [ ] 完整运行录像
- [ ] 构建日志
- [ ] 无TD无Spout扫描
- [ ] 正式门负测试报告

## 完成条件

E0开发环境和会话壳可复现并向U-01与U-02交付接口且不成为研究流程权威

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
