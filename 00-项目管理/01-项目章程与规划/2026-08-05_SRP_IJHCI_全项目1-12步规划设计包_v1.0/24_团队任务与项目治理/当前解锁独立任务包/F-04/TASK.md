# F-04 【TouchDesigner】只读操作台壳

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：
- 分支：`codex/<task-id>-<short-name>`
- 第二复核人：
- 领取时间：

## 任务边界

- 领域：TouchDesigner
- 波次：W0
- 状态：`READY`
- 类型：FIXED
- 预计工作量：2人日
- 前置依赖：无
- 所需技能：TouchDesigner+DAT+CHOP+操作台
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-TD B站TouchDesigner零基础课程检索入口](https://search.bilibili.com/all?keyword=TouchDesigner%20%E9%9B%B6%E5%9F%BA%E7%A1%80)

## 交付物

- 会话设备波形质量时钟模块降级页面骨架
- 只读标记

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [ ] AC1静态fixture可演示全部页面
- [ ] AC2关闭TD不影响其他制品
- [ ] AC3不存在Spout输出随机化或阈值编辑入口

## 必需证据

- [ ] toa/toe版本
- [ ] 页面截图
- [ ] 节点权限检查

## 完成条件

只读壳经另一人操作复核

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：
- 验证命令与结果：
- 证据路径：
- commit：
- push目标：
- 剩余风险：
