# SRP · 实验体验与论文证据系统

> 四天气场景 · 两种呼吸提示方案 · 真实设备输入 · 可追溯研究证据

SRP面向短时负性情绪调节的交互研究，比较**场景原生提示**与**抽象控件式提示**的收益、代价与适用边界，不预设哪种方案获胜。项目由4人混合团队推进，以阶段一支撑一篇独立IJHCI目标论文，阶段二、三保留为条件式扩展。

## 版本与进度

<!-- TEAM_PROGRESS_START -->
### 团队任务进度图

升级工作线进度：20项DONE；A-03进行中；U12-03待签收；6项READY。图源为升级工作线`852cfd8`，不是main历史注册表的完成声明。

[![团队任务进度图](assets/readme/team-task-progress.svg)](assets/readme/team-task-progress.svg)

点击图可打开原始SVG放大查看。任务状态变化时同步更新本区块、下方状态表和SVG。
<!-- TEAM_PROGRESS_END -->

**更新日期：2026-09-08。** 以下进度对应升级工作线 [73ffbf5](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/README.md)，不是声称这些实现已经合并到 `main`。本次首页更新仅同步说明与导航；主分支内的历史文档仍保留其原验收范围。

| 项目 | 升级工作线状态 |
|---|---|
| 任务规模 | 71项：68项固定任务、3项批次模板 |
| 已签收 | 20项DONE，包含U12-01治理迁移与U12-02步骤实例测量 |
| 进行中 | A-03；其A-03-SPEC里程碑已签收 |
| 待签收 | U12-03公平教学合同：独立Agent复核PASS，仍为IN_REVIEW |
| 可领取 | Q-01、T-02、U-02、U12-04、U12-06、U12-07 |
| 研究准入 | 真实设备、机构资格、正式数值和教学时序仍待完成或冻结 |

[查看任务注册表](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/00-%E9%A1%B9%E7%9B%AE%E7%AE%A1%E7%90%86/01-%E9%A1%B9%E7%9B%AE%E7%AB%A0%E7%A8%8B%E4%B8%8E%E8%A7%84%E5%88%92/2026-08-05_SRP_IJHCI_%E5%85%A8%E9%A1%B9%E7%9B%AE1-12%E6%AD%A5%E8%A7%84%E5%88%92%E8%AE%BE%E8%AE%A1%E5%8C%85_v1.0/24_%E5%9B%A2%E9%98%9F%E4%BB%BB%E5%8A%A1%E4%B8%8E%E9%A1%B9%E7%9B%AE%E6%B2%BB%E7%90%86/05_%E5%8F%AF%E9%A2%86%E5%8F%96%E4%BB%BB%E5%8A%A1%E5%8C%85.csv) · [领取独立任务包](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/00-%E9%A1%B9%E7%9B%AE%E7%AE%A1%E7%90%86/01-%E9%A1%B9%E7%9B%AE%E7%AB%A0%E7%A8%8B%E4%B8%8E%E8%A7%84%E5%88%92/2026-08-05_SRP_IJHCI_%E5%85%A8%E9%A1%B9%E7%9B%AE1-12%E6%AD%A5%E8%A7%84%E5%88%92%E8%AE%BE%E8%AE%A1%E5%8C%85_v1.0/24_%E5%9B%A2%E9%98%9F%E4%BB%BB%E5%8A%A1%E4%B8%8E%E9%A1%B9%E7%9B%AE%E6%B2%BB%E7%90%86/%E5%BD%93%E5%89%8D%E8%A7%A3%E9%94%81%E7%8B%AC%E7%AB%8B%E4%BB%BB%E5%8A%A1%E5%8C%85/README.md) · [查看团队任务图](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/04-%E6%88%90%E6%9E%9C%E4%B8%8E%E4%BA%A4%E4%BB%98/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B%E5%9B%BE/SRP_%E9%A1%B9%E7%9B%AE%E4%BB%BB%E5%8A%A1%E5%85%B3%E8%81%94%E4%B8%8E%E9%97%A8%E7%A6%81%E6%B5%81%E7%A8%8B_v1.0.svg)

上述链接固定到本次核对的提交，避免首页引用尚未合并、在main不存在的文件。持续开发请查看[升级工作分支](https://github.com/JunyeFu/Emotional-Healing-System/tree/codex/u12-03-fair-training)及其任务注册表。

## 体验与研究设计

- **四个固定镜头场景**：storm风暴、heat炙烤、snow暴雪、fade褪色；每种天气一个核心视觉机制。
- **两种完整提示方案**：`scene_native`与`abstract_pacer`；分别表达目标、实际、累计与输入不可用信息。
- **核心体验推荐800秒**：每模块25秒示范、150秒闭环、25秒锁定与转场，四模块各一次。
- **参与者无需手部操作**：体验中平坐观看并跟随呼吸提示；前后测与理解测量安排在体验之外。
- **阶段一顺序预先均衡分配**：体验中的数据不重新决定场景顺序；每人只参加一个阶段、一个条件和一次核心体验。
- **证据分工**：前后PANAS支持情绪结果分析；真实生理记录支持执行质量及过程分析；理解和负担帮助解释适用边界。

U12-03提出两臂相同的180秒教学候选，正式预算仍未冻结。候选时序为共同准备 → PANAS前测 → 分配揭示 → 分条件教学 → 核心体验 → PANAS后测 → 理解及其他测量。

## 系统分工

```text
真实设备 → Python：采集、交互状态估计、会话编排与追加记录
                    ├─ Unity：独立参与者体验、四层反馈与渲染回执
                    └─ TouchDesigner：监控、可视化及受审计的操作请求

原始记录 + 问卷 + 分配与回执 → 离线处理 → 分析、图表与论文证据
```

Python是流程与时间权威。Unity不依赖TD提供画面；TD不能直接改变研究流程。实际数据缺失保持缺失，不能用目标、零值或模拟输入补齐。开发fixture仅用于开发和故障验证。

## 开发与交付入口

| 内容 | 已核对版本入口 |
|---|---|
| 研究主线与升级边界 | [v1.2治理说明](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/00-%E9%A1%B9%E7%9B%AE%E7%AE%A1%E7%90%86/01-%E9%A1%B9%E7%9B%AE%E7%AB%A0%E7%A8%8B%E4%B8%8E%E8%A7%84%E5%88%92/2026-08-05_SRP_IJHCI_%E5%85%A8%E9%A1%B9%E7%9B%AE1-12%E6%AD%A5%E8%A7%84%E5%88%92%E8%AE%BE%E8%AE%A1%E5%8C%85_v1.0/24_%E5%9B%A2%E9%98%9F%E4%BB%BB%E5%8A%A1%E4%B8%8E%E9%A1%B9%E7%9B%AE%E6%B2%BB%E7%90%86/u12_upgrade/README.md) |
| 研究候选参数 | [protocol_authority_v1.2.json](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/00-%E9%A1%B9%E7%9B%AE%E7%AE%A1%E7%90%86/01-%E9%A1%B9%E7%9B%AE%E7%AB%A0%E7%A8%8B%E4%B8%8E%E8%A7%84%E5%88%92/2026-08-05_SRP_IJHCI_%E5%85%A8%E9%A1%B9%E7%9B%AE1-12%E6%AD%A5%E8%A7%84%E5%88%92%E8%AE%BE%E8%AE%A1%E5%8C%85_v1.0/00_%E6%80%BB%E6%8E%A7/protocol_authority_v1.2.json) |
| 运行协议与步骤身份 | [F-05 v2.2接口基线](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/02-%E6%8A%80%E6%9C%AF%E7%A0%94%E5%8F%91/05-%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE/contracts/F-05_v2.2%E6%8E%A5%E5%8F%A3%E5%AF%B9%E9%BD%90%E5%9F%BA%E7%BA%BF.md) |
| Python会话编排 | [P-01 SessionCore](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/02-%E6%8A%80%E6%9C%AF%E7%A0%94%E5%8F%91/srp_session_core/README.md) |
| 追加存储与确定性重放 | [P-02 SessionStore](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/02-%E6%8A%80%E6%9C%AF%E7%A0%94%E5%8F%91/srp_session_store/README.md) |
| 数据治理与权限 | [G-02](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/02-%E6%8A%80%E6%9C%AF%E7%A0%94%E5%8F%91/07-%E6%95%B0%E6%8D%AE%E6%B2%BB%E7%90%86/README.md) |
| 步骤实例理解测量 | [U12-02](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/02-%E6%8A%80%E6%9C%AF%E7%A0%94%E5%8F%91/srp_step_measurement/README.md) |
| 公平教学与形成性比较 | [U12-03教学合同](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/00-%E9%A1%B9%E7%9B%AE%E7%AE%A1%E7%90%86/01-%E9%A1%B9%E7%9B%AE%E7%AB%A0%E7%A8%8B%E4%B8%8E%E8%A7%84%E5%88%92/2026-08-05_SRP_IJHCI_%E5%85%A8%E9%A1%B9%E7%9B%AE1-12%E6%AD%A5%E8%A7%84%E5%88%92%E8%AE%BE%E8%AE%A1%E5%8C%85_v1.0/24_%E5%9B%A2%E9%98%9F%E4%BB%BB%E5%8A%A1%E4%B8%8E%E9%A1%B9%E7%9B%AE%E6%B2%BB%E7%90%86/u12_upgrade/U12-03_fair_training/README.md) |
| 团队工具版本 | [环境冻结基线](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/00-%E9%A1%B9%E7%9B%AE%E7%AE%A1%E7%90%86/01-%E9%A1%B9%E7%9B%AE%E7%AB%A0%E7%A8%8B%E4%B8%8E%E8%A7%84%E5%88%92/2026-08-05_SRP_IJHCI_%E5%85%A8%E9%A1%B9%E7%9B%AE1-12%E6%AD%A5%E8%A7%84%E5%88%92%E8%AE%BE%E8%AE%A1%E5%8C%85_v1.0/24_%E5%9B%A2%E9%98%9F%E4%BB%BB%E5%8A%A1%E4%B8%8E%E9%A1%B9%E7%9B%AE%E6%B2%BB%E7%90%86/11_%E5%9B%A2%E9%98%9F%E5%B7%A5%E5%85%B7%E4%B8%8E%E7%8E%AF%E5%A2%83%E5%86%BB%E7%BB%93%E5%9F%BA%E7%BA%BF_v1.0.md) |
| 完整任务概要 | [任务概要PDF](https://github.com/JunyeFu/Emotional-Healing-System/blob/73ffbf5/output/pdf/02_%E5%9B%BA%E5%AE%9A%E4%BB%BB%E5%8A%A1%E6%A6%82%E8%A6%81.pdf) |

## 验证与使用边界

升级工作线最近一次根Python回归为**633项通过**，U12-03专项为**22项通过**。这是代码与合同一致性证据，不代表真实设备全链、参与者理解、正式研究或论文录用已经通过。

在对应升级版本、按环境基线配置依赖后，可运行：

```powershell
Set-Location 'D:\Agent\03-SRP'
git status --short
py -3.14 -m pytest -q
git diff --check
```

当前不是一键可开展正式实验的发布包。旧`main.py`、UDP v1.2及Spout链只作历史原型参考，不作为新研究启动入口。正式体验不依赖LLM或编辑器开发桥。
