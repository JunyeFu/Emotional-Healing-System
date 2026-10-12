# 人类审阅层

当前71包证据审阅及[项目串联审阅](project-review.pdf)统一维护为 LaTeX + PDF，不再维护对应 DOCX。每包同目录提供 `summary.tex` 与 `summary.pdf`，正文、成员视频截图、图注及历史签收记录沿用执行层事实。项目背景见[当前项目概览](project/README.md)。

标题采用居中加粗黑体，正文采用微软雅黑；字体嵌入 PDF。各包按“一、任务定义与交付”“二、执行与验证”“三、审阅与交接”及“1.1、2.1、3.1”分层。迁移验证见[本次记录](../agent/evidence/task-latex-migration.json)。

事实先维护 `agent/tasks/<编号>/outputs/summary.json`，再运行 `python agent/tools/build_task_reviews.py <编号>` 生成该包及串联审阅；`ALL` 重建全部，`ALL --check` 检查全部。排版维护 `agent/tools/review_latex.py`；使用 XeLaTeX，字体来自本机 `C:/Windows/Fonts/`。串联源文件见[project-review.tex](project-review.tex)。

当前可复用模板：[LaTeX v5.0](templates/通用中文逐包任务模板_v5.0.tex) · [PDF预览](templates/通用中文逐包任务模板_v5.0.pdf) · [填写与编译说明](templates/README.md)。

旧[通用任务模板](templates/通用中文逐包任务模板_v4.0.docx)、历史签署原件及输入快照保留为历史参考，当前证据审阅不再以 Word 为入口。任务业务状态以注册表为准。

当前71包已按新基线刷新，详见[迁移记录](../agent/work/2026-10-08_新基线任务包迁移.md)。本表当前审阅描述任务修订及真实缺口；历史状态/签收不自动覆盖新增范围。

| 顺序 | 任务包 | 当前审阅 | 新范围处理 |
|---|---|---|---|
| 1 | F-01 I/G/X控制与遥测语义修订 | [PDF](tasks/F-01/summary.pdf) · [LaTeX](tasks/F-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 2 | F-02 构念、情绪与公平执行测量 | [PDF](tasks/F-02/summary.pdf) · [LaTeX](tasks/F-02/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 3 | F-03 Unity资产与新双条件环境基线 | [PDF](tasks/F-03/summary.pdf) · [LaTeX](tasks/F-03/summary.tex) | 保留功能、澄清用途；原DONE只保留原范围 |
| 4 | F-04 双设备只读预览与显示边界 | [PDF](tasks/F-04/summary.pdf) · [LaTeX](tasks/F-04/summary.tex) | 保留功能、澄清用途；原DONE只保留原范围 |
| 5 | F-05 I/G/X事件与受限适应步骤合同 | [PDF](tasks/F-05/summary.pdf) · [LaTeX](tasks/F-05/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 6 | G-01 五人团队与后续阶段资源规划 | [PDF](tasks/G-01/summary.pdf) · [LaTeX](tasks/G-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 7 | G-02 新反馈用途的数据与许可治理 | [PDF](tasks/G-02/summary.pdf) · [LaTeX](tasks/G-02/summary.tex) | 保留功能、澄清用途；原DONE只保留原范围 |
| 8 | P-01 I/G分离与受限控制的会话编排 | [PDF](tasks/P-01/summary.pdf) · [LaTeX](tasks/P-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 9 | P-02 理想、引导、实际及适应成本记录 | [PDF](tasks/P-02/summary.pdf) · [LaTeX](tasks/P-02/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 10 | U-01 Unity控制镜像与实际呈现回执 | [PDF](tasks/U-01/summary.pdf) · [LaTeX](tasks/U-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 11 | U-02 固定与原生自适应呈现适配 | [PDF](tasks/U-02/summary.pdf) · [LaTeX](tasks/U-02/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 12 | T-01 双设备只读显示服务于新测量 | [PDF](tasks/T-01/summary.pdf) · [LaTeX](tasks/T-01/summary.tex) | 保留功能、澄清用途；原DONE只保留原范围 |
| 13 | R-01 固定开环与原生自适应整包设计 | [PDF](tasks/R-01/summary.pdf) · [LaTeX](tasks/R-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 14 | V-01 同预算的完整参与者旅程 | [PDF](tasks/V-01/summary.pdf) · [LaTeX](tasks/V-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 15 | V-02 Storm/Fade优先的场景设计 | [PDF](tasks/V-02/summary.pdf) · [LaTeX](tasks/V-02/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 16 | V-03 开环与闭环的视听映射 | [PDF](tasks/V-03/summary.pdf) · [LaTeX](tasks/V-03/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 17 | V-04 新条件配对预演与教学材料 | [PDF](tasks/V-04/summary.pdf) · [LaTeX](tasks/V-04/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 18 | D-01 H10辅助测量及额外成本 | [PDF](tasks/D-01/summary.pdf) · [LaTeX](tasks/D-01/summary.tex) | 保留功能、澄清用途；原WAIT_DEP_EXTERNAL只保留原范围 |
| 19 | D-02 respiBAN实际呼吸可辨性 | [PDF](tasks/D-02/summary.pdf) · [LaTeX](tasks/D-02/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
| 20 | S-01 真实质量与双设备同步 | [PDF](tasks/S-01/summary.pdf) · [LaTeX](tasks/S-01/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 21 | S-02 独立X事件与I/G公平计分 | [PDF](tasks/S-02/summary.pdf) · [LaTeX](tasks/S-02/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 22 | V-05 固定/受限适应全旅程灰盒 | [PDF](tasks/V-05/summary.pdf) · [LaTeX](tasks/V-05/summary.tex) | 修订待实证；原READY只保留原范围 |
| 23 | U-03 Fade复杂步骤原生自适应切片 | [PDF](tasks/U-03/summary.pdf) · [LaTeX](tasks/U-03/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 24 | U-04 剩余天气A按新条件适配 | [PDF](tasks/U-04/summary.pdf) · [LaTeX](tasks/U-04/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 25 | U-05 剩余天气B按新条件适配 | [PDF](tasks/U-05/summary.pdf) · [LaTeX](tasks/U-05/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 26 | U-06 剩余天气C按新条件适配 | [PDF](tasks/U-06/summary.pdf) · [LaTeX](tasks/U-06/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 27 | U-07 固定圈开环方案的可信对照 | [PDF](tasks/U-07/summary.pdf) · [LaTeX](tasks/U-07/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 28 | U-08 产品预算、可访问与净收益 | [PDF](tasks/U-08/summary.pdf) · [LaTeX](tasks/U-08/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 29 | T-02 操作台消费I/G/X及研究许可 | [PDF](tasks/T-02/summary.pdf) · [LaTeX](tasks/T-02/summary.tex) | 修订待实证；原READY只保留原范围 |
| 30 | A-01 I/G/X原始证据离线重建 | [PDF](tasks/A-01/summary.pdf) · [LaTeX](tasks/A-01/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 31 | A-02 新条件执行与缺失统计 | [PDF](tasks/A-02/summary.pdf) · [LaTeX](tasks/A-02/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 32 | A-03 新整包比较SAP与样本精度 | [PDF](tasks/A-03/summary.pdf) · [LaTeX](tasks/A-03/summary.tex) | 修订待实证；原IN_PROGRESS只保留原范围 |
| 33 | W-01 原创性与最近工作全文审查 | [PDF](tasks/W-01/summary.pdf) · [LaTeX](tasks/W-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 34 | I-01 两设备与新条件真实完整链 | [PDF](tasks/I-01/summary.pdf) · [LaTeX](tasks/I-01/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
| 35 | Q-01 构念与多步骤独立重建材料 | [PDF](tasks/Q-01/summary.pdf) · [LaTeX](tasks/Q-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 36 | Q-02 校园需求与方案认知访谈 | [PDF](tasks/Q-02/summary.pdf) · [LaTeX](tasks/Q-02/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 37 | Q-03 真实技术和受限适应预试 | [PDF](tasks/Q-03/summary.pdf) · [LaTeX](tasks/Q-03/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
| 38 | X-01 新两臂随机化与阶段人数 | [PDF](tasks/X-01/summary.pdf) · [LaTeX](tasks/X-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 39 | X-02 可选离线策略学习的延期边界 | [PDF](tasks/X-02/summary.pdf) · [LaTeX](tasks/X-02/summary.tex) | 可选扩展延期；原WAIT_DEP只保留原范围 |
| 40 | X-03 可选策略运行与首版受限控制分工 | [PDF](tasks/X-03/summary.pdf) · [LaTeX](tasks/X-03/summary.tex) | 可选扩展延期；原WAIT_DEP只保留原范围 |
| 41 | Z-01 新双条件候选制品与重建 | [PDF](tasks/Z-01/summary.pdf) · [LaTeX](tasks/Z-01/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 42 | G-05 新研究用途外部准入 | [PDF](tasks/G-05/summary.pdf) · [LaTeX](tasks/G-05/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
| 43 | E-01 Level A专家与独立重建执行 | [PDF](tasks/E-01/summary.pdf) · [LaTeX](tasks/E-01/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 44 | E-02 Level B需求与认知活动执行 | [PDF](tasks/E-02/summary.pdf) · [LaTeX](tasks/E-02/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 45 | B-01 Level C真实预试批次模板 | [PDF](tasks/B-01/summary.pdf) · [LaTeX](tasks/B-01/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 46 | E-03 新控制与测量技术关闭 | [PDF](tasks/E-03/summary.pdf) · [LaTeX](tasks/E-03/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 47 | G-03 新两臂正式协议与预注册 | [PDF](tasks/G-03/summary.pdf) · [LaTeX](tasks/G-03/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 48 | B-02 新协议正式阶段批次模板 | [PDF](tasks/B-02/summary.pdf) · [LaTeX](tasks/B-02/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 49 | E-04 新条件阶段一锁库与揭盲 | [PDF](tasks/E-04/summary.pdf) · [LaTeX](tasks/E-04/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 50 | A-05 新整包阶段一锁定分析 | [PDF](tasks/A-05/summary.pdf) · [LaTeX](tasks/A-05/summary.tex) | 修订待实证；原BLOCKED_EXTERNAL只保留原范围 |
| 51 | E-05 可选学习策略的独立冻结 | [PDF](tasks/E-05/summary.pdf) · [LaTeX](tasks/E-05/summary.tex) | 可选扩展延期；原BLOCKED_EXTERNAL只保留原范围 |
| 52 | G-04 可选策略扩展的独立准入 | [PDF](tasks/G-04/summary.pdf) · [LaTeX](tasks/G-04/summary.tex) | 可选扩展延期；原BLOCKED_EXTERNAL只保留原范围 |
| 53 | B-03 可选扩展批次模板 | [PDF](tasks/B-03/summary.pdf) · [LaTeX](tasks/B-03/summary.tex) | 可选扩展延期；原BLOCKED_EXTERNAL只保留原范围 |
| 54 | E-06 可选扩展关闭与揭盲 | [PDF](tasks/E-06/summary.pdf) · [LaTeX](tasks/E-06/summary.tex) | 可选扩展延期；原BLOCKED_EXTERNAL只保留原范围 |
| 55 | A-04 可选扩展独立锁定分析 | [PDF](tasks/A-04/summary.pdf) · [LaTeX](tasks/A-04/summary.tex) | 可选扩展延期；原BLOCKED_EXTERNAL只保留原范围 |
| 56 | A-06 核心贡献及阶段范围关闭 | [PDF](tasks/A-06/summary.pdf) · [LaTeX](tasks/A-06/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 57 | W-02 整包收益与目标代价论文主稿 | [PDF](tasks/W-02/summary.pdf) · [LaTeX](tasks/W-02/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 58 | W-03 实际贡献的期刊匹配与提交准备 | [PDF](tasks/W-03/summary.pdf) · [LaTeX](tasks/W-03/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 59 | W-04 科研产品实践的真实移交 | [PDF](tasks/W-04/summary.pdf) · [LaTeX](tasks/W-04/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 60 | U12-01 新任务设计权威与原执行范围治理 | [PDF](tasks/U12-01/summary.pdf) · [LaTeX](tasks/U12-01/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 61 | U12-02 条件适配的步骤测量材料 | [PDF](tasks/U12-02/summary.pdf) · [LaTeX](tasks/U12-02/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 62 | U12-03 固定与原生自适应公平教学 | [PDF](tasks/U12-03/summary.pdf) · [LaTeX](tasks/U12-03/summary.tex) | 修订待实证；原IN_REVIEW只保留原范围 |
| 63 | U12-04 新PANAS与执行代价SAP | [PDF](tasks/U12-04/summary.pdf) · [LaTeX](tasks/U12-04/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 64 | U12-05 新材料静态及回放真实准入 | [PDF](tasks/U12-05/summary.pdf) · [LaTeX](tasks/U12-05/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
| 65 | U12-06 新方案正式入口与运行许可衔接 | [PDF](tasks/U12-06/summary.pdf) · [LaTeX](tasks/U12-06/summary.tex) | 修订待实证；原IN_PROGRESS只保留原范围 |
| 66 | U12-07 结果前中立写作及审稿修复 | [PDF](tasks/U12-07/summary.pdf) · [LaTeX](tasks/U12-07/summary.tex) | 修订待实证；原DONE只保留原范围 |
| 67 | U12-08 可选扩展独立附录 | [PDF](tasks/U12-08/summary.pdf) · [LaTeX](tasks/U12-08/summary.tex) | 可选扩展延期；原WAIT_DEP只保留原范围 |
| 68 | U12-09 71包新基线覆盖一致性 | [PDF](tasks/U12-09/summary.pdf) · [LaTeX](tasks/U12-09/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 69 | U12-10 整包结果分轴解释规则 | [PDF](tasks/U12-10/summary.pdf) · [LaTeX](tasks/U12-10/summary.tex) | 修订待实证；原WAIT_DEP只保留原范围 |
| 70 | U12-11 新研究参数与资源冻结 | [PDF](tasks/U12-11/summary.pdf) · [LaTeX](tasks/U12-11/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
| 71 | U12-12 成果选择与社会价值判断 | [PDF](tasks/U12-12/summary.pdf) · [LaTeX](tasks/U12-12/summary.tex) | 修订待实证；原WAIT_DEP_EXTERNAL只保留原范围 |
