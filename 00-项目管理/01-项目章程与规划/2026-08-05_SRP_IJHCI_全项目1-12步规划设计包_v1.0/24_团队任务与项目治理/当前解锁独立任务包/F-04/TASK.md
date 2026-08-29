# F-04 【TouchDesigner】模块化与图形化只读操作台

> 状态权威仍是[05_可领取任务包.csv](../../05_可领取任务包.csv)。本包输入为生成时快照，实际修改必须发生在`FILES.md`列出的项目权威路径。

## 领取登记

- 领取人：Codex Agent（F-04独立对话）
- 分支：`codex/f-04-readonly-console`
- 第二复核人：傅钧烨（团队总监，独立第二人复核人）
- 领取时间：历史登记未记录；当前不得重复领取

## 任务边界

- 领域：TouchDesigner
- 波次：W0
- 状态：`IN_REVIEW`
- 类型：FIXED
- 预计工作量：3人日
- 前置依赖：无
- 所需技能：TouchDesigner+DAT+CHOP+操作台
- 涉及文件与工作目录：见[FILES.md](FILES.md)

## 学习资料

- [L-TD B站TouchDesigner零基础课程检索入口](https://search.bilibili.com/all?keyword=TouchDesigner%20%E9%9B%B6%E5%9F%BA%E7%A1%80)

## 交付物

- 升级控制文件
- ConsoleShell与统一ConsoleSnapshot接口
- 10页图形化只读工作台
- 5场景静态适配器
- 禁用T-01与T-02占位

## 四阶段过程

1. 读取依赖制品并先建立失败测试或golden fixture。
2. 只在所属模块内实现最小完整纵向能力。
3. 运行正常、异常、重连或权限负测试。
4. 整理代码、文档、证据并提交第二人验收。

## 验收要求

- [x] AC1十页可见导航与五场景切换且只读标识常驻
- [x] AC2呼吸页为CHOP曲线且其余页面具有对应图形机制
- [x] AC3页面仅通过ConsoleSnapshot取数且适配器可替换
- [x] AC4关闭TD后5005和9981无监听且请求控件禁用
- [x] AC5无Spout网络输出随机化阈值编辑Unity输出或请求发送回调
- [x] AC6真实TD构建保存重开无错误且截图齐全
- [ ] AC7傅钧烨独立操作并签署PASS或FAIL — `PENDING_DIRECTOR_REVIEW`

## 必需证据

- [x] 升级控制文件
- [x] toe/tox及哈希
- [x] 接口与场景矩阵测试
- [x] 节点计划清单权限错误报告
- [x] 十四张截图
- [x] 端口检查
- [x] 合同与相关回归
- [ ] 第二人签收 — `PENDING_DIRECTOR_REVIEW`

## 完成条件

AC1至AC7关闭且傅钧烨签署PASS后方可转DONE

完成还必须满足：第二人复核、相关验证通过、证据路径可访问，并完成本任务范围内的commit与push。

## 完成回填

- 实际改动文件：见`FILES.md`列出的项目权威路径
- 验证命令与结果：技术候选已完成；模型复核状态`PENDING_DIRECTOR_REVIEW`
- 证据路径：`02-技术研发/03-TouchDesigner/f04_readonly_console/F-04_技术验收记录.md`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/host/host_build_manifest.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/host/page_manifest.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/host/node_plan.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/host/node_permissions.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/node_errors.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/node_inventory.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/runtime_build_manifest.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/reopen_report.json`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/01_session_version.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/02_device_connection.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/03_respiration_waveform.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/04_ecg_rr_quality.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/05_phase_comparison.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/06_cycle_result.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/07_latency_clock.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/08_degradation.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/09_log_write.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/10_manual_actions.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/11_degradation_degraded_heat.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/12_degradation_unusable_snow.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/13_degradation_disconnected_fade.png`；`02-技术研发/03-TouchDesigner/f04_readonly_console/evidence/touchdesigner/screenshots/14_degradation_out_of_order_storm.png`
- commit：`b910a0d0b04147c228263b444b1beecb5a27ba2d`
- push目标：`origin/codex/f-04-readonly-console`
- 剩余风险：真实团队第二人签署及任务文档列明的外部边界仍开放
