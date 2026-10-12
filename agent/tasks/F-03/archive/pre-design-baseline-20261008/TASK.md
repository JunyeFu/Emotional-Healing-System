# F-03【Unity】可复现工程与测试构建基线


## 责任与验收

当前实施要求：以Unity 2022.3.62f3重建工程恢复、包锁和Edit/Play/Windows开发构建入口；旧Unity6测试只保留历史证明。采用[统一实现标准](../../design/情绪天气方案/2026-10-08_Storm与纯粒子双环实施标准.md)，截图与核查边界见[本包画面证据](outputs/current-implementation-evidence.md)。

原领取人为Codex Agent（F-03独立对话），真实第二人为傅钧烨。本轮Codex负责脚本迁移、当前复测、证据整理和人类Word。

- AC1：锁定Unity版本及包依赖，环境漂移失败。
- AC2：Edit/Play测试与Windows开发构建可重复，制品明确DEV-REPLAY。
- AC3：不依赖TD/Spout，正式门或未授权Development路径拒绝发布。

## 执行

1. 从inputs/sources.json读取共享Unity模块与历史证据。inputs中的环境锁是唯一当前锁文件。
2. 确认工作树干净，运行execution/verify.ps1；它执行Pester及完整Unity基线工具。
3. 本轮运行写入evidence/runtime，不覆盖已签收历史证据。构建产物在Unity工程Builds中且不提交。
4. 将真实结果写入outputs/summary.json，再生成人类Word与项目串联审阅，逐页检查。

## 下游

F-01/F-05提供线格式；P-01仍是研究流程与时钟权威。U-01实现协议消费者，U-02实现四层场景接口，V-05构造全旅程灰盒。F-03只提供工程、测试与开发构建基线，不代替它们的完成证据。

## 当前目录

execution是原Tools/F03脚本的唯一活动位置，旧目录移除，不新增兼容入口。共享Unity代码和历史签署保留原位置，最终全项目路径迁移时统一处理。
