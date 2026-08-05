# SRP × IJHCI 小任务树 v1.0

> 单个任务包建议1–5人日。成员自主领取，但必须遵守依赖、接口和验收条件。

## M0 研究治理

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M0.1 | 冻结版本命名与变更流程 | VERSIONING.md | 能判定MAJOR/MINOR/PATCH | 无 |
| M0.2 | 建立实验发布清单 | release checklist | 一次空跑全部通过 | M0.1 |
| M0.3 | 建立问题与偏离登记 | deviation log template | 可记录伦理/协议/实现偏离 | 无 |

## M1 数据契约与随机化

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M1.1 | 实现Manifest读写 | Python/Unity loader | 示例Manifest均可解析 | Schema |
| M1.2 | 实现事件信封 | Python/Unity logger | 1000事件无顺序冲突 | Schema |
| M1.3 | 随机化与分配隐藏 | schedule + key | 相同seed完全复现；8单元均衡 | 无 |
| M1.4 | 会话目录与校验和 | session packager | 自动生成SHA256 | M1.1–M1.2 |
| M1.5 | QC报告生成 | qc_report.json | 能识别Mock、缺模块、乱序 | M1.4 |

## M2 Python真实设备链

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M2.1 | 呼吸设备适配器 | raw respiration stream | 连续30分钟无静默中断 | 设备 |
| M2.2 | ECG/RR适配器 | raw ECG/RR stream | 时间戳完整、断流可见 | 设备 |
| M2.3 | 时钟服务 | sync telemetry | Unity/Python偏差≤50ms | M1.2 |
| M2.4 | 信号质量模块 | SQI + reasons | 伪迹/断流产生明确状态 | M2.1 |
| M2.5 | 呼吸事件检测 | event stream | Level C标注门 | M2.1 |
| M2.6 | 协议调度器 | target phases | 四模块时间线一致 | protocol YAML |
| M2.7 | 反馈与累计恢复 | actual/recovery state | 周期反馈与累计层分离 | M2.4–M2.6 |
| M2.8 | 会话状态机 | orchestrator | 合法/非法转换测试通过 | M1.1 |

## M3 Unity参与者体验

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M3.1 | Manifest与控制客户端 | Unity components | 版本握手失败时拒绝启动 | M1.1 |
| M3.2 | 目标/实际/累计/降级四层 | common controllers | 参数互不覆盖 | M2.7 |
| M3.3 | 风暴原生提示 | Storm adapter | 四阶段可辨识 | M3.2 |
| M3.4 | 炙烤原生提示 | Heat adapter | 长呼气可辨识 | M3.2 |
| M3.5 | 暴雪原生提示 | Snow adapter | 5-5对称可辨识 | M3.2 |
| M3.6 | 褪色原生提示 | Fade adapter | 双吸结构预试可辨识 | M3.2 |
| M3.7 | 抽象双环节律器 | Abstract pacer | 等信息量审查通过 | M3.2 |
| M3.8 | 安全降级与中止 | fallback UI | Python失联可安全退出 | M3.1 |
| M3.9 | 渲染遥测 | render events | P95延迟可计算 | M1.2 |

## M4 TouchDesigner实验员台

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M4.1 | 遥测接收与版本显示 | TD receiver | 不影响Unity主链 | M2 |
| M4.2 | 波形、目标和实际相位 | monitoring views | 一屏可辨识 | M4.1 |
| M4.3 | SQI与降级告警 | alerts | 断流5秒内告警 | M4.1 |
| M4.4 | 人工事件标记 | operator marker | 只写事件，不改参数 | M1.2 |
| M4.5 | 中止请求 | stop request | Python确认后执行 | M2.8 |

## M5 研究测量与预试

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M5.1 | SCCI专家审查表 | CVI workbook/template | I-CVI/S-CVI可计算 | 第2步 |
| M5.2 | 认知访谈材料 | script + coding guide | 目标/实际/累计可编码 | M5.1 |
| M5.3 | 实验员SOP | session manual | 新实验员可按步骤执行 | 第3步 |
| M5.4 | 安全筛查与不良事件表 | forms | 伦理审查可提交 | 第3步 |
| M5.5 | Level C人工标注工具 | annotation UI | 两标注员独立操作 | M2.5 |
| M5.6 | Level C自动QC | dashboard/report | 技术门自动汇总 | M1.5 |

## M6 分析与复现

| ID | 任务 | 输出 | 验收 | 依赖 |
|---|---|---|---|---|
| M6.1 | L0→L3派生流水线 | scripts | 同输入产生同输出 | M1/M2 |
| M6.2 | FAS/PPS生成器 | locked tables | 排除理由可审计 | M6.1 |
| M6.3 | Gate 1模型骨架 | GLMM script | 合成数据可运行 | M6.2 |
| M6.4 | Gate 2模型骨架 | mixed model script | 合成数据可运行 | M6.2 |
| M6.5 | 数据集发布器 | release folder | 校验和和版本完整 | M6.2 |
| M6.6 | 论文图表自动生成 | figures | 不手工修改数据 | M6.3–M6.4 |

## 领取规则

1. 先领取接口和验证明确的任务。
2. 一个任务未通过验收，不得宣称其依赖任务完成。
3. 修改主张、量表、协议或伦理边界必须回到科研设计文件。
4. 每个任务完成后执行测试、commit、push。
5. 任何正式实验相关代码必须经过第二人审查。
