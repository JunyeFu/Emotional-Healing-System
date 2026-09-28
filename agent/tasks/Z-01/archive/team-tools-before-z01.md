# 四人团队工具与环境冻结基线 v1.0

> 冻结日期：2026-08-06
>
> 修订：2026-08-06（澄清Unity、TouchDesigner和Python数据处理栈为全员基线）
>
> 修订：2026-08-06（Zotero改为论文与设计负责人必装、全员共享访问）
>
> 状态：`ACTIVE_FOR_TEAM_SETUP`
>
> 机器可读权威：[team_tool_baseline_v1.0.json](team_tool_baseline_v1.0.json)
>
> 校验器：[validate_team_tool_baseline.py](../99_验证与清单/validate_team_tool_baseline.py)

## 1. 决策原则

1. 全员使用同一Windows、Git、Unity、TouchDesigner、Python数据处理栈、编辑器和引用管理基线，保证每个人都能打开、运行、检查和交接项目的完整链路。
2. 四人的工具可用范围相同，岗位差异只定义主要职责和验收深度，不允许用“非本岗位”为由省略Unity、TouchDesigner或Python数据处理环境。
3. 精确版本在一个任务周期内禁止个人单独升级；需要升级时必须同时修改机器清单、依赖文件、验证记录和受影响制品。
4. 工具已安装只代表环境入口可用，不代表Unity制品、真实设备链、Level、Gate或研究结果成立。
5. 当前项目唯一有效目录为`D:\Agent\03-SRP`。所有校验、提交和制品路径均从该目录执行。

## 2. 四人都必须具备的公共基线

| 工具 | 冻结版本 | 版本策略 | 用途 |
|---|---|---|---|
| Windows 11 x64 | `10.0.26100+` | 兼容下限；每次证据记录实际Build，不要求补丁号完全相同 | Unity、TD、BLE和正式运行平台 |
| PowerShell | `7.6.4` | 精确版本 | 项目脚本、Git与环境检查 |
| Git for Windows | `2.54.0.windows.1` | 精确版本 | 分支、提交、审查与发布 |
| Git LFS | `3.7.1` | 精确版本 | Unity及大型制品跟踪 |
| OpenSSH for Windows | `9.5p2` | 精确版本 | GitHub SSH访问 |
| Python x64 | `3.14.4` | 精确版本 | 校验器、数据工具和任务脚本 |
| pip | `26.1.1` | 精确版本 | Python依赖安装 |
| pytest | `9.0.3` | 精确版本 | 项目回归和任务验收 |
| Visual Studio Code x64 | `1.131.0` | 精确版本；关闭个人抢先升级 | Markdown、Python、JSON、CSV和Git审查 |
| Unity Editor | `6000.4.9f1`，revision `f7258d6eebbe` | 精确版本；以项目`ProjectVersion.txt`为权威 | 运行完整Unity体验、检查场景、回放数据和复核构建 |
| TouchDesigner x64 | `2025.32820` | 精确版本 | 打开操作台、回放数据、检查记录与实时可视化 |
| Python数据处理栈 | [requirements-baseline-py3.14.txt](../../../../02-技术研发/requirements-baseline-py3.14.txt)中的9项直接依赖 | 精确直接依赖 | 采集桥接、交互状态估计、数据质控、统计准备和项目验证 |

全员还必须具备GitHub仓库访问权限、个人SSH密钥和Zotero共享库的只读或更高权限。Unity与Python/数据负责人可以通过Zotero Web Library完成共享访问验收，不要求本机安装Zotero。访问凭据不写入仓库，也不由版本号代替权限验收。

Unity项目包统一冻结为Universal RP `17.4.0`、Input System `1.19.0`、Cinemachine `3.1.7`和Unity Test Framework `1.6.0`。所有成员打开项目时不得自行升级或重写包锁。

## 3. 全员同装后的岗位能力重点

以下内容只划分主要责任，不减少任何人的安装要求。每个人都必须通过第5节的同一套本机环境检查；负责人还要完成其岗位任务包规定的操作证据。

Zotero是本节的唯一岗位安装例外：设计负责人和承担论文证据治理的实验/TD/治理负责人必须安装Zotero x64 `9.0.6`（[官方版本历史](https://www.zotero.org/support/changelog)）。其他成员不要求安装，但必须能打开共享库、检索项目集合并访问一条指定文献记录。

### 3.1 设计负责人

- 主要负责在Unity中打开两种完整提示表示方案、检查四层可见信息、导出审查截图和Level材料。
- 能在TouchDesigner中读取操作台视图，并运行Python校验器复核设计数据是否可追踪。
- 使用Zotero `9.0.6`维护设计依据、来源等级和引用导出，不使用个人孤立文献库替代共享库。

### 3.2 Unity负责人

- 主要负责Play Mode、自动化测试、Windows x64构建、Profiler证据和Unity制品完整用户体验。
- 能使用TouchDesigner和Python回放同一数据，定位Unity输入、时钟或显示异常属于哪一层。
- MCP for Unity固定到当前解析提交`78ee5418415953b79c358bfe6355fcc3fde7912b`，仅作编辑器自动化；最终验收仍以Unity测试、构建、日志和录像为准。

`Packages/manifest.json`中的Unity MCP仍引用`#main`，但`packages-lock.json`记录了当前解析提交。该写法存在重新解析漂移风险，在F-03或首次包变更前必须改为固定提交或形成等价的离线包证据。旧KlakSpout包不属于目标运行依赖，不能把Spout可用写成Unity完成条件。

### 3.3 Python/数据负责人

主要负责采集桥接、交互状态估计、数据质控、统计准备和可复现数据处理。下列依赖必须安装在四人的Python 3.14环境中，而不仅是Python/数据负责人：

| 包 | 冻结版本 |
|---|---:|
| numpy | `2.4.6` |
| scipy | `1.17.1` |
| pandas | `2.3.3` |
| matplotlib | `3.10.9` |
| NeuroKit2 | `0.2.13` |
| BioSPPy | `2.2.4` |
| bleak | `3.0.2` |
| PeakUtils | `1.3.5` |
| pytest | `9.0.3` |

这些版本来自当前已通过42项项目回归的本机直接依赖快照。当前文件只冻结直接依赖；正式LIVE_E2E前还必须生成完整传递依赖锁和干净环境重建证据。

### 3.4 实验/TD/治理负责人

- 主要负责TouchDesigner只读操作台、静态fixture回放，以及波形、质量、时钟和降级信息检查。
- 能启动同版本Unity制品并核对TD记录与Unity体验使用的是同一场次、同一协议和同一时钟来源。
- 作为论文证据治理负责人，使用Zotero `9.0.6`维护许可、来源、招募与论文证据索引，并运行Python校验、fixture和日志检查。

仓库保留的TouchDesigner MCP版本为`v1.4.7`，但它只属于自动化辅助，不是F-04验收前提。当前机器未安装该服务的`connexion`/Flask依赖，因此不得把MCP目录存在写成TD自动化已就绪。

## 4. 不纳入全员基线的工具

| 工具 | 当前版本/状态 | 裁定 |
|---|---|---|
| Codex Desktop | 当前中枢机`26.730.8199.0` | 只要求Agent操作者具备，不要求四人各自安装 |
| Node.js / npm | 当前中枢机`24.15.0` / `12.0.1` | 当前首波任务不依赖；只有MCP维护任务明确需要时才冻结 |
| Unity Hub | 当前中枢机未发现 | 不作为验收条件；Editor精确版本和项目revision才是权威 |
| TouchDesigner MCP | 仓库`v1.4.7`，服务依赖未就绪 | 可选自动化，不代替TD操作台证据 |
| Zotero x64 | `9.0.6` | 不纳入全员本机安装；设计与论文证据治理负责人必装，其他成员完成共享库访问验收 |
| Microsoft Word或其他办公软件 | 未冻结 | Markdown、CSV、BibTeX是当前源文件；W-02/W-03再冻结投稿工具 |

## 5. 每人领取任务前的最低验收

1. 在`D:\Agent\03-SRP`运行`git status --short`，能够看到当前用户工作区状态。
2. 运行公共环境检查；该模式检查Unity、TouchDesigner和Python数据处理栈，不要求Zotero本机安装：

   ```powershell
   py -3.14 "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/99_验证与清单/validate_team_tool_baseline.py" --local-role common
   ```

3. 正式领取时把`common`替换为`design`、`unity`、`python_data`或`experiment_td_governance`。其中`design`和`experiment_td_governance`追加检查Zotero `9.0.6`，其余技术工具检查保持一致。
4. 四人都要完成共享文献访问人工验收：打开项目共享库、检索验收人指定的集合和记录，并把账号、文献内容等敏感信息遮蔽后的访问证据附入首个任务包。
5. 验收输出、实际OS Build、工具路径和偏差原因写入任务证据，不允许只发安装截图。
6. 任一精确版本不一致时，先形成升级或降级记录；不得让工具自动改写Unity包锁、Python直接依赖或Zotero共享库格式后再补说明。

## 6. 当前中枢机审计

| 项 | 当前值 | 对基线 |
|---|---|:---:|
| Windows | `10.0.26200` x64 | PASS |
| PowerShell | `7.6.4` | PASS |
| Git / Git LFS | `2.54.0.windows.1` / `3.7.1` | PASS |
| OpenSSH | `9.5p2` | PASS |
| Python / pip / pytest | `3.14.4` / `26.1.1` / `9.0.3` | PASS |
| VS Code | `1.131.0` | PASS |
| Unity | `6000.4.9f1`，revision `f7258d6eebbe` | PASS |
| TouchDesigner | `2025.32820` | PASS |
| Python直接依赖 | 9项版本与冻结表一致 | PASS |
| Zotero | 未发现安装 | COMMON_NOT_REQUIRED / DESIGN_OR_PAPER_ROLE_GAP |
| TD MCP服务依赖 | 未安装 | OPTIONAL_NOT_READY |

因此当前中枢机的自动化公共工具基线通过。若该机器由设计负责人或论文证据治理负责人使用，仍需安装Zotero `9.0.6`；若由其他岗位使用，则只需另行完成共享文献访问人工验收。当前审计未验证任何成员的共享库权限。

## 7. 升级规则

1. 工具升级必须由一个独立任务包提出，写明原因、受影响制品、回滚路径和验证命令。
2. 先在独立分支更新机器清单和依赖锁，再运行项目回归、Unity测试或TD回放。
3. 全员工具须四人均完成版本迁移；岗位工具须所有必装岗位完成版本迁移后，才能修改本文件的冻结版本。不得在同一工具范围内长期混用两个精确版本。
4. Windows安全补丁可以不同，但实际Build必须进入每次LIVE_E2E环境记录。
5. Zotero升级由论文证据治理负责人发起，必须先备份共享库并与设计负责人共同验证BibTeX导出差异；其他成员的Web Library访问也要复核。
