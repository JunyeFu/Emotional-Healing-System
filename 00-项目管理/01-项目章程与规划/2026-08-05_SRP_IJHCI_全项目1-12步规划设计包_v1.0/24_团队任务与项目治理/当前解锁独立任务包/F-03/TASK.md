# F-03 【Unity】可复现工程与测试构建基线

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex Agent（F-03独立对话）
- 分支：`codex/f-03-unity-baseline`
- 第二复核人：傅钧烨（团队总监，独立第二人复核人）
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：Unity
- 波次：W0
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：无
- 所需技能：Unity+C#+Edit/Play Mode+环境复现+构建
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-UNITY Unity中文手册](https://docs.unity3d.com/cn/2023.2/Manual/index.html)
- [L-UNITYTEST Unity Test Framework中文手册](https://docs.unity3d.com/cn/2023.2/Manual/testing-editortestsrunner.html)

## 交付物

- 精确Unity与包锁环境报告
- 基线编译与Edit/Play测试架
- 可重复Windows开发构建链
- DEV-REPLAY标记
- 无TD无Spout依赖扫描
- 资产阻断基线

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [x] AC1精确Unity和包锁可在干净工作区恢复并编译且漂移失败关闭
- [x] AC2Edit/Play测试与Windows开发构建可重复执行且所有开发制品清晰标记DEV-REPLAY
- [x] AC3关闭TD与Spout后开发构建仍可启动且正式模式缺manifest或资产门失败关闭

## 必需证据

- [x] Unity环境报告
- [x] 包锁哈希
- [x] 测试XML
- [x] 构建日志
- [x] DEV-REPLAY截图
- [x] 无TD无Spout扫描
- [x] 正式门负测试报告
- [x] 运行身份报告
- [x] 同次资产报告
- [x] 本地构建收据
- [x] F-01负测试日志

## 完成条件

可复现工程与测试构建基线向U-01 U-02和V-05交付且不预设天气方案或研究流程

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PASS_FOR_MODEL_INDEPENDENT_REVIEW`
- 证据路径：`03-测试与实验/F-03_技术验收记录_待签署.md`；`03-测试与实验/evidence/F-03/evidence_manifest.json`；`03-测试与实验/evidence/F-03/evidence_hashes.sha256`；`03-测试与实验/evidence/F-03/environment_report.json`；`03-测试与实验/evidence/F-03/run_identity_report.json`；`03-测试与实验/evidence/F-03/build_artifact_receipt.json`；`03-测试与实验/evidence/F-03/editmode-results.xml`；`03-测试与实验/evidence/F-03/playmode-results.xml`；`03-测试与实验/evidence/F-03/repeat_build_report.json`；`03-测试与实验/evidence/F-03/run-1-build-manifest.json`；`03-测试与实验/evidence/F-03/run-2-build-manifest.json`；`03-测试与实验/evidence/F-03/player_smoke_report.json`；`03-测试与实验/evidence/F-03/dev-replay-player.png`；`03-测试与实验/evidence/F-03/runtime_dependency_scan.json`；`03-测试与实验/evidence/F-03/formal_negative_report.json`；`03-测试与实验/evidence/F-03/asset_blocking_report.json`
- commit：`a61eba6a62631780caaf60d8e2e431326d3082ba`
- push目标：`origin/codex/f-03-unity-baseline`
- 剩余风险：真实团队第二人签署及任务文档列明的外部边界仍开放
