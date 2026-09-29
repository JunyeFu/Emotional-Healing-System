# V-05 【Unity预制作】四模块全旅程灰盒与形成性回退门

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：未领取
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：未指定
- 领取时间：未领取

## 任务边界

- 领域：Unity预制作
- 波次：W2
- 状态：`READY`
- 类型：FIXED
- 预计工作量：5人日
- 前置依赖：F-03、U-02、V-04
- 所需技能：Unity灰盒+DEV-REPLAY+流程验证+形成性评审
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)
- [L-RESEARCH 中国大学MOOC研究方法课程检索入口](https://www.icourse163.org/search.htm?search=%E7%A0%94%E7%A9%B6%E6%96%B9%E6%B3%95)

## 交付物

- 四模块全旅程灰盒
- 24顺序自动检查
- 两条件占位实现
- 构图视线节奏转场检查
- 形成性问题与回退记录

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1使用DEV-REPLAY记录fixture完成任意合法manifest顺序且四模块各一次不依赖参与者操作
- [ ] AC2简单色块占位声音和标签即可核对构图提示节奏转场及两条件信息匹配
- [ ] AC3关键不理解遮挡节奏断裂或条件不匹配必须回退V-02至V-04关闭且评审人员不进入正式样本

## 必需证据

- [ ] Unity Edit/Play测试
- [ ] 24顺序报告
- [ ] 完整灰盒录像
- [ ] 形成性评审表
- [ ] 问题关闭矩阵

## 完成条件

全旅程灰盒通过后才允许U-03投入接近最终质量的垂直切片

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
