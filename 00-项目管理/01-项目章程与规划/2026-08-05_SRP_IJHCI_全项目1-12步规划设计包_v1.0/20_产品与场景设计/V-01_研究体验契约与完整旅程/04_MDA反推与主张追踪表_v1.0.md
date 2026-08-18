# V-01 MDA 反推与主张追踪表 v1.0

## 方法

本表从期望体验反推运行动态，再反推 Unity 可实现机制。任何显著设计主张都必须归入以下一类：

- `RESEARCH_VARIABLE`：属于计划比较或条件操纵，必须进入分析计划和公平审计。
- `RUNTIME_EVIDENCE`：用于证明系统实际呈现了什么，不直接构成效果结论。
- `NON_RESEARCH_DECORATION`：只支持完成度，不得被写成研究贡献，也不能系统性区分条件。

同一元素若跨类，按风险最高的 `RESEARCH_VARIABLE` 管理。

## MDA 反推表

| ID | 期望体验 Aesthetics | 需要形成的 Dynamics | Unity Mechanics | 分类 | 可验证证据 |
|---|---|---|---|---|---|
| M-001 | 不学习技术术语也能跟随 | 目标节律在每模块开始先被理解 | `demo` 段、目标层动画、相位边界 | RESEARCH_VARIABLE | 提示跟随 PF、理解题、段级回执 |
| M-002 | 能觉察目标与自身当前状态的差异 | 目标与实际同步变化但保持可区分 | 两条独立渲染通道，共享上游时钟 | RESEARCH_VARIABLE | F-02 真值、帧级遥测、条件截图 |
| M-003 | 感到变化具有连续积累 | 快速相位与慢速累计变化同时存在 | 单调累计映射、模块末锁定 | RESEARCH_VARIABLE | `recovery_value/recovery_locked` 轨迹 |
| M-004 | 数据不稳定时仍理解发生了什么 | 可靠性下降不会变成虚假正常 | 四级 fallback 映射和中性保持态 | RESEARCH_VARIABLE | 故障注入、理解结果、原因码 |
| M-005 | 场景原生条件像完整环境机制 | 四层信息融入环境且仍可辨认 | 每模块唯一核心视觉机制 | RESEARCH_VARIABLE | SCCI、理解、负担与公平审计 |
| M-006 | 抽象条件清楚但不压过场景 | 抽象提示独立、稳定、信息等价 | V-02 决定的抽象表示组件 | RESEARCH_VARIABLE | SCCI、理解、负担与公平审计 |
| M-007 | 四模块像一次连续旅程 | 模块完成后自动收束并进入下一模块 | `lock_transition`、共用转场语法、连续声景 | RUNTIME_EVIDENCE | 19 个控制事件轨迹、回执、录像 |
| M-008 | 偏离目标时不被评价 | 实际轨迹可偏离但没有得分、警告或失败标签 | 非评价性颜色与运动语法 | RESEARCH_VARIABLE | 文案审查、理解访谈、录屏 |
| M-009 | 无需操作也不会失去流程 | 所有推进由外部权威确定 | 只读 Unity 状态机、无参与者输入处理 | RUNTIME_EVIDENCE | 输入扫描、状态机测试、会话重放 |
| M-010 | 暂停或故障时不被技术信息打断 | 场景进入可辨认的稳定保持态 | 暂停覆盖层或环境保持机制 | RUNTIME_EVIDENCE | 故障脚本、错误码、回执 |
| M-011 | 环境具有一致的审美完成度 | 色彩、材质、镜头与音色遵守同一系统 | V-03 视觉系统与音频规范 | NON_RESEARCH_DECORATION | 设计评审和资产清单 |
| M-012 | 入口和结束具有完整感 | 核心材料只在 start 后出现，结束不宣告个人效果 | 中性入口、完成画面、淡入淡出 | RUNTIME_EVIDENCE | 启动门负测试、结束回执 |

## 主张追踪表

| Claim ID | 候选主张 | 类别 | 对应变量或证据 | 允许的结论边界 | 当前状态 |
|---|---|---|---|---|---|
| C-001 | 场景原生完整表示包可在维持提示跟随功能下提升场景融合感 | RESEARCH_VARIABLE | 第一阶段 PF 非劣门、SCCI 有序主张 | 只能比较完整表示包 | DESIGN_HYPOTHESIS_NOT_OBSERVED |
| C-002 | 场景原生完整表示包不会以明显理解损失或负担增加换取融合感 | RESEARCH_VARIABLE | 理解非劣门、负担非劣门 | 需按预注册门控顺序判断 | DESIGN_HYPOTHESIS_NOT_OBSERVED |
| C-003 | 四层表示能让参与者区分目标、实际、累计与降级 | RESEARCH_VARIABLE | F-02 理解题、状态真值 | 不能在正式数据前写成已证实 | DESIGN_HYPOTHESIS_NOT_OBSERVED |
| C-004 | 自动四模块旅程按 manifest 完整执行 | RUNTIME_EVIDENCE | 控制事件、ACK、回执、最终状态哈希 | 只证明执行一致性 | ENGINEERING_CANDIDATE |
| C-005 | Unity 在无 TouchDesigner 画面时可完成参与者体验 | RUNTIME_EVIDENCE | 独立构建、网络拓扑与验收录像 | 只证明产品独立性 | ENGINEERING_CANDIDATE |
| C-006 | 场景内累计变化支持连续感 | RESEARCH_VARIABLE | SCCI 分项、访谈、累计轨迹 | 当前只作为设计假设 | DESIGN_HYPOTHESIS_NOT_OBSERVED |
| C-007 | 特定天气与特定呼吸流程的组合具有独立效果 | RESEARCH_VARIABLE | 当前设计不提供可识别的独立对照 | 不得提出该独立因果结论 | OUT_OF_SCOPE |
| C-008 | 某一顺序优于其他顺序 | RESEARCH_VARIABLE | 仅在第三阶段策略研究完成后按冻结分析判断 | 第一阶段不得得出该结论 | CONDITIONAL_STAGE_3 |
| C-009 | 粒子、角色或背景细节提升研究效果 | NON_RESEARCH_DECORATION | 无计划独立变量 | 不进入论文主贡献 | OUT_OF_SCOPE |
| C-010 | 前后量表变化与体验中真实记录可共同描述项目参与后的短期变化 | RESEARCH_VARIABLE | 前后量表、质量门后的设备记录和缺失机制 | 不替代对完整表示包与顺序的计划比较 | DESIGN_HYPOTHESIS_NOT_OBSERVED |

## 设计到证据的硬规则

1. `RESEARCH_VARIABLE` 必须有唯一 ID、条件差异说明、分析变量和公平审计入口。
2. `RUNTIME_EVIDENCE` 必须能够关联 `session_id`、构建哈希、控制事件和渲染回执。
3. `NON_RESEARCH_DECORATION` 在两条件间保持一致，或证明差异不改变信息、显著度和行为。
4. 没有证据路径的设计主张只能写入创作动机，不能写入研究结论。
5. 天气是四个固定复合实例的载体，不是自动获得独立效应解释的因素。
