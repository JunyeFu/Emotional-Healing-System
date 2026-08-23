# Codex Blackboard

> Purpose: lightweight project-local working memory for the current task. Keep this file factual, brief, and easy to reset.

## Current Task Goal

四项IN_REVIEW已由傅钧烨第二人签收`PASS`（签收提交`ea132c8`）：P-01、P-02转`DONE`，F-05解锁为`READY`；G-01（AC3演练/U8/M-001许可/伦理）、G-02（专机/保留期限/197项资产门）保持`IN_REVIEW`，外部门关闭前不得转`DONE`。当前可领取：F-03、F-04、F-05、V-03。

## Constraints

- 不修改全局 Codex 配置。
- 不安装 hooks。
- 不写入长期 memory。
- 不覆盖已有项目规则。
- 本次不移动或删除 Unity、TD、实验材料、参考文献及用户未跟踪文件。
- 已有 4 个删除项、`CLAUDE.md` 修改、`SRP/` 和根目录 docx 均视为用户改动。
- 保留 SRP 术语边界，避免新增禁用表达。
- 不导出内部隐式推理；以“观察—判断—影响”记录可审计依据。
- 完成后验证文件存在、入口引用有效、术语扫描和 `git diff --check` 通过。
- 仅在`D:\Agent\03-SRP`操作；保留四个既有删除项、`SRP/`、根目录docx、`tmp/`和本地Unity日志，不纳入G-02提交。
- G-02不得在专机环境、保留期限、Unity资产和真实团队第二人复核关闭前标记为`DONE`。

## Known Evidence

- 2026-08-21 G-01：对`origin/main`根目录8个文件的验收不通过（记录于`03-测试与实验/G-01_验收记录_2026-08-21.md`）；随后按流程领取，基于`codex/v-02-concept-design`建`codex/g-01-research-governance`（`origin/main`注册表落后，不作基底）。
- G-01返工：8文件归位`06_步骤05_伦理与预试材料/`，补齐G-01-01与G-01-10；v1.1时长口径统一（PANAS 2~3、猜测2~3、问卷≤5、知情同意5~8、清理5~8）；演练口径统一（窗口14天/执行7天、产能140、U8线112、预约165）；责任人角色化（R-007）；术语0命中；`07`/`14`校验通过，pytest 404 passed。
- G-01边界：AC3真实演练未执行、U8未判定、M-001许可`PENDING`、第二人复核开放；转`IN_REVIEW`不扩大为DONE或正式阶段放行。

- Git 根目录为 `D:/Agent/03-SRP`，本任务开始时 HEAD 为 `97ed1e8`，分支为 `main`。
- `PROJECT_MODULES.md` 仍把 TD Spout 作为 Unity 输入；后续访谈已确认 Unity 必须脱离 TD 独立完成体验，因此模块地图需要在主线确认后另行修订。
- 旧科研确认稿仍记录每场景 7 分钟、8-12 人等早期方案；当前访谈已将场景约束改为 90-120 秒，并提出 `4×4` 平衡设计。
- 后续访谈已用“一种天气固定对应一种呼吸法”的复合模块顺序研究覆盖独立 `4×4` 组合建议。
- 用户已确认当前处于理想目标反推的重设计阶段；现状缺口不限制目标高度，但必须作为实施门禁。
- 用户已确认“一篇主论文、一项会议或交互展示、三个运行制品、一套科研资产、一项软件著作权、一个条件性专利成果和一套展示材料”的最终成果基线。
- 用户允许系统在策略确认阶段根据真实交互状态估计为不同参与者生成不同合法顺序，并分析完整顺序及转换作用。
- 用户已将第一阶段进一步冻结为 24 种完整顺序均衡随机：参与前量表只用于分层和平衡，真实设备数据在本阶段不改变场景顺序。
- 第二阶段使用探索数据学习并冻结可解释策略；第三阶段使用新参与者至少与均衡随机基准独立比较。
- 用户已确认前后量表变化承担整体变化和顺序作用检验，真实设备数据承担复合模块过程响应和呼吸执行质量分析；两者使用不同模型，不合成为一个总指标。
- 固定天气—呼吸配对不能识别呼吸法脱离视觉天气后的独立作用；当前设备分析对象必须表述为呼吸执行质量和复合模块过程响应。
- 用户已确认唯一主要量表构念为状态性负面情绪变化；SAM 的愉悦度、唤醒度、控制感以及正性情绪等只作为次要结果，不参与主要得分合成。
- 用户已采用经中文人群验证的 20 项 PANAS；参与前后均使用“此刻”时间框架，10 项负性情绪分量表承担唯一主要量表结果，10 项正性情绪分量表为次要结果。
- 用户已确认 `ΔNA = NA_pre - NA_post`，正值表示状态性负面情绪下降；主要顺序推断使用 `NA_post ~ NA_pre + 预先定义的随机顺序特征`，原始变化值用于描述和稳健性分析。
- 用户已确认位置效应和 12 种有向相邻转换承担主要结构化分析；24 种完整顺序报告校正后估计、区间与排名稳定性，但不作为 24 组未经结构化的主要比较。
- 策略学习联合位置、转换、参与前状态和真实设备过程特征；冻结后在新参与者中与均衡随机基准独立比较。
- 用户已确认 `MPT` 相对 `M0` 为唯一全局主要检验；通过后再以 Holm 校正检验位置效应组和转换增量效应组，对应效应组通过后才解释具体比较。
- 全局检验未通过时，位置、转换和 24 种完整顺序只能作为探索性估计报告；未预注册分析必须显式标记为探索结果。
- 用户已确认唯一全局主要检验使用 `90%` 目标功效和双侧 `alpha = 0.05`，样本量通过实际24顺序满秩设计矩阵的蒙特卡洛模拟获得。
- 非正式预实验只估计方差、前后相关性、残差和不可用比例等干扰参数；不直接使用预实验观察作用作为正式功效输入。有效样本量向上取24的整数倍，招募量另加不可用会话预留。
- 只读秩检查显示位置块为9个自由度、控制位置后的转换增量为5个自由度，`MPT` 相对 `M0` 的顺序结构合计14个自由度。
- 用户已确认全局增量效应使用 `f²=(R²_MPT-R²_M0)/(1-R²_MPT)`，敏感性网格为0.02/0.05/0.10，主要规划情景为0.05，不可用会话预留为15%。
- 非中心 F 前置近似得到：0.02情景1176个有效会话/1384次招募，0.05情景480/565，0.10情景264/311。该结果不是正式蒙特卡洛结论。
- 用户已确认降低确认性主模型复杂度：24种完整顺序仍均衡随机，14自由度位置与转换模型降为次要分析和策略学习模型，唯一确认性顺序问题改为少量预先定义的理论对比。
- U34 样本量只代表14自由度模型作为主要检验时的需求；修正后样本量必须在理论对比冻结后重新计算。
- 当前模块证据仍有“暴雪：稳定呼吸+微行动”和“褪色：自主呼吸+感官连接”，前者与全程无手部操作冲突，后者缺少与其他模块同等明确的标准化节律。
- 天气变化设计已进一步核对：风暴是风雨/闪电衰减与保护罩修复，炙烤是热浪衰减与冷色气流进入，暴雪是雪雾遮蔽降低与路径显现，褪色是去饱和状态与色彩光点恢复。
- 联网证据支持约每分钟6次的慢节律作为稳健过程基线，并要求把固定 `5-5` 与需要个体评估的共振频率呼吸区分开。
- 结构化呼吸随机研究给出了循环叹息和箱式流程，但其每日5分钟、持续28天的结果不能直接外推到单段120秒。
- 2024年吸呼比原始与重复研究未发现6次/分下 `1:2` 相对 `1:1` 的 HRV 优势；`4-6` 应作为可比较形态，不能预设更强。
- 用户已确认映射基线：风暴—`3-3-3-3` 箱式、炙烤—`4-6`、暴雪—`5-5`、褪色—循环叹息。
- 该确认冻结研究设计中的四组对应关系，但正式运行参数仍须通过说明理解、舒适度、目标达成、真实设备可辨识和退出规则门禁；调整必须版本化并重新确认。
- 固定配对只识别天气—呼吸复合模块及其顺序作用，不能拆分声称单一呼吸流程脱离天气后的独立作用。
- 暴雪脚印由 Unity 旅人自动产生，不恢复参与者微行动；参与者继续保持平坐并跟随呼吸。
- 用户已确认移除参与者侧统一呼吸圈、双圈 HUD 和 TD Spout 呼吸圈纹理；入场示范也使用场景原生机制。
- 风暴保护罩/风雨、炙烤冷却气流/热浪、暴雪脚印路径/雪雾、褪色色彩扩散/饱和度分别承担目标节律提示和实时反馈。
- 真实设备断流或质量不足时，Unity 必须继续以当前场景原生机制提供开环目标节律或中性降级提示，并记录降级事件；具体规则尚未冻结。
- TD 只保留实验员侧波形、相位、误差和数据质量监控，不向参与者画面输出必要纹理。
- 用户已确认弹性时长设计，取代固定 `15 + 90 + 15秒`：示范目标25秒（24至30秒）、实时闭环目标150秒（140至160秒）、锁定转场目标25秒（20至30秒）。
- 单模块目标200秒、允许184至220秒；四模块目标13分20秒、允许约12分16秒至14分40秒。
- 区间只用于技术预试和构建选择；同一正式阶段必须冻结具体时长，两个提示条件保持一致，不得按参与者或实时状态动态改变。
- 会话必须记录计划时长、实际阶段边界和偏差原因；不同呼吸流程实际周期数作为流程差异保留。
- 跨制品日志至少需要模块、顺序位置、模块时间、阶段、分析资格、转场来源/目标和降级状态字段；正式字段名后续冻结。
- 呼吸周期的局部往复反馈和天气恢复的段内累积进度必须分层，避免全局天气随吸气和呼气来回跳变。
- `3-3-3-3` 是面向初次参与者和120秒模块的保守候选；四流程仍需理解度、舒适度、执行质量和真实设备可辨识门禁。
- Unity 场景文档仍保留 TD Spout 呼吸圈依赖，与已确认的 Unity 独立体验目标不一致，后续架构修订必须处理。
- 先前“天气—呼吸复合序列因果评估与可解释自适应优化”的核心贡献表述已被 U40 覆盖；因果评估和自适应优化本身分别属于研究设计和系统能力，不能脱离新的设计知识或方法独立成立。
- 用户已确认主论文核心贡献一为场景原生呼吸引导框架，其可复用映射语法依次覆盖目标呼吸阶段、场景原生提示、周期级真实反馈、段内累计环境变化和场景原生降级。
- 用户已确认核心贡献二为可解释闭环序列编排方法；方法必须显式定义并版本化状态、动作、概率、决策理由、数据窗口、回退条件和可离线重放记录，不能停留在不可审计的条件分支。
- 第一阶段24顺序均衡随机、第二阶段策略学习与冻结、第三阶段冻结策略对均衡随机的独立比较共同构成证据链，不再与核心贡献并列。
- 固定天气—呼吸配对仍只能识别复合模块及其顺序；没有合理基准时不能声称场景原生提示更优，没有独立策略比较时不能声称自适应编排更优。
- 下一道门是冻结核心贡献一的唯一主要经验主张及其最小比较基准；低自由度顺序对比、检验层级和样本量随后围绕该主张重新定义。
- 新增 `00-项目管理/看板与进度/2026-08-04_项目情况与顶层设计汇总.md`，作为当前仓库情况、目标产品、论文贡献、实验数据链、论文叙事、成果组合、职责方向和未决门的集中入口。
- 汇总明确旧阶段7看板和旧 TD Spout 呼吸圈链路属于 `As-Is` 证据，不代表 `To-Be` 目标已经实现；理想顶层设计不以当前实现缺口为上限。
- 当时抽象节律提示基准、`protocol_fidelity`、非劣界值和完整项目第三比较条件均为建议；后续用户已确认抽象基准与 `protocol_fidelity`，其余项目仍未确认。
- 下一道 Grill 门修正为先冻结因果主张范围，再确定最小比较基准；只有此后才能冻结主要设备结果和样本量。
- 本次完整 Python 回归实测为 `42 passed in 8.21s`。

## Risks

- 访谈中的早期意见和后期决定可能冲突，记录必须显式区分状态，不能覆盖历史。
- 用户已有删除项可能属于进行中的材料调整，不得恢复或提交。
- 顶级期刊录用、展示录取和专利授权属于外部结果，只能承诺投稿稿件、申报材料与证据质量。
- 正式实验目标使用真实设备数据；Mock 只保留开发验证用途，不能混入正式数据。
- 第一阶段若让实时数据改变顺序，就不再是 24 种完整顺序等概率探索；该机制只能在冻结策略后的独立确认阶段启用并记录选择概率。
- 三阶段结构不能替代主要结果、样本量、数据质量和多重分析控制；高水平录用仍不可预先保证。
- 将设备过程差异直接归因于呼吸法会越过固定配对设计的识别能力；若未来要求分离作用，必须改变组合设计或增加专门比较条件。
- 既有材料中的 SAM 不能因实施简短而自动升级为主要得分；具体量表仍需核查构念匹配、中文版本证据、授权和即时变化敏感性。
- PANAS 方案确认不等于实施证据完成；中文版题项来源、版本、计分说明和使用许可必须在正式采集前核验并冻结。
- 在缺少不经历完整项目流程的比较条件时，原始前后下降不能单独归因于项目；随机顺序之间的校正后比较只识别顺序分配的差异。
- 位置与转换包含多个相关系数；若不预先定义联合假设和检验层级，仍会产生多重分析和事后筛选风险。
- 主要检验层级已经冻结，但位置与转换编码仍需证明满秩；编码不当会导致不可估计系数或错误自由度。
- 预实验观察作用通常不稳定，不能据此缩小正式样本；最小关注效应必须独立冻结并做敏感性分析。
- 主要规划情景约需565次招募，明显超出旧方案8-12人的规模；若无大规模招募能力，当前确认性模型不可执行，不能靠乐观效应假设掩盖。
- 降低自由度必须来自预先确定的设计理论，不能为了缩小样本量而根据正式结果挑选对比。
- 天气—呼吸映射来自节律形态与视觉机制的一致性，是待验证的跨模态设计假设，不应写成既有论文已经证明的自然配对。
- 当前目标150秒实时闭环可支持执行质量与时域轨迹分析；若使用场景级频域HRV，仍需单独验证窗口长度，不能自动按常规短时记录解释。
- 箱式流程的停顿和循环叹息的连续双吸可能带来个体不适；未通过舒适度门禁前不能冻结正式参数。
- 移除统一呼吸圈后需要分别验证四套原生提示；任何一个场景的相位可辨识或初次理解失败，都会直接影响呼吸执行质量和模块可比性。
- 旧 Unity 设计与工程仍保留 TD Spout 呼吸圈依赖；在主线完成前只记录为待重构旧基线，不能误认为目标架构已经实现。
- 若转场段强制显示完全恢复，会把脚本时间效应混入真实设备闭环结果；已冻结为锁定105秒累计状态后转场，后续实现不得改变该语义。
- 140至160秒主要过程窗口预计提供约12至16个目标周期；预试仍须验证各流程相位、周期边界和有效周期比例的可辨识性。
- 若只展示四个场景实现而没有抽取、跨实例检验场景原生映射语法，核心贡献一会退化为作品说明。
- 若闭环编排缺少形式化状态、选择概率、版本、理由、回退和重放记录，核心贡献二会退化为普通系统功能。
- 场景原生提示若没有合理比较基准，只能支持可行性、可辨识性和设计知识，不能支持优越性主张。
- 冻结策略若没有在新参与者中与均衡随机基准独立比较，只能支持策略形成过程，不能支持自适应增益主张。
- 汇总文件同时包含现状与目标；若读者忽略状态标签，可能把旧制品能力或尚未确认的研究建议误解为已完成目标。
- 旧阶段看板尚未切换到顶层重设计状态；在正式阶段门确认前，汇总只记录差异，不擅自覆盖历史看板。

## 2026-08-05 IJHCI规划包导入与重新梳理

### Goal

将Downloads中的全项目1至12步规划包作为完整候选基线归档到项目管理模块，保留原件和哈希；阅读包内主线、模块、路线和执行附件；同步记录判断；重新建立用户确认门。

### Evidence

- 源包137个文件、414291字节；首次复制后相对路径和SHA-256差异为0。
- 原始Grill记录U40确认两项长期贡献，U41当时将抽象对照、`protocol_fidelity`、非劣设计和样本量保留为未确认；后续用户已确认前两项。
- 包内功效脚本复算得到Gate 1为24至64个有效配对，Gate 2在`d_z=0.35`时为88个有效配对，15%预留并按8人取整为104人。
- 第五步材料包结构验证PASS，保留32个机构字段占位。
- 第六步路由包结构验证PASS，`routing_confirmed=false`，`formal_participant_recruitment_allowed=false`。
- 第四步整包验证因项目环境缺少`jsonschema`而未运行完成；依赖未在执行包中声明。

### Current Decision Boundary

- 已确认：8分钟四模块、无手部操作、场景原生四层视觉、真实设备正式数据、Unity/Python/TD/离线职责、固定配对解释边界、24顺序与独立策略确认长期方向。
- 待确认：首篇论文是否只比较场景原生与抽象提示，并把序列编排移到后续独立论文。
- 该主线确认前，不冻结双门控结果、两实验日交叉和104人，也不拆四人任务包。

### Risks

- 包内“冻结”“GO”和步骤1至5完成标签可能被误读为用户决定或现实完成。
- 104人的数学链可复现，但依赖自建SCCI、`d_z=0.35`价值判断和Level C干扰参数。
- 两实验日方案需要208次访问，现场工时和流失风险尚未确认。
- 原包结构报告、文件清单和实际源文件数有不同统计口径。

### Next Gate

原确认门（已被用户后续决定取代）：是否采用“首篇验证场景原生提示框架，后续独立验证可解释序列编排”的分阶段主线。

### User Decision Update

- 用户已否决分论文路线，确认最终只写一篇IJHCI论文。
- 两个贡献点必须分出主次后融合到同一篇论文。
- 用户已确认：场景原生呼吸提示框架为主贡献，可解释序列编排为次贡献。
- 序列次分析聚焦位置、前序天气和相邻转换效应；不以稀疏的24组均值直接宣称最佳顺序。
- 该主次确认门已关闭。
- 用户已确认保留 `abstract_pacer`：抽象呼吸圈承担节律提示与实时相位反馈，天气保留同等宏观响应但不得编码呼吸相位。
- 两条件只改变提示与相位反馈载体，天气、声音、呼吸法、时长、顺序、算法和宏观响应强度保持一致。
- 用户已否决同一参与者重复参与：第一次参与可能改变第二次访问的短期情绪基线，访问间隔不能可靠消除残留影响。
- 两实验日参与者内交叉、88个有效配对、104人和208次访问方案全部失效；样本量必须按组间主效应重新计算。
- 用户要求先按阶段回查天气顺序设计，单阶段1:1方案暂停。
- 原始已确认设计：阶段一每个分层内24完整顺序以 `1/24` 均衡随机且不受实时数据改变；阶段二只用阶段一数据学习并冻结策略；阶段三用新参与者比较冻结策略与24顺序均衡随机基准。
- 后来四序列Williams方案依赖“序列编排另写论文”的已失效前提，不能作为当前基线。
- 用户已确认三阶段映射：阶段一两个提示条件各自平衡24顺序；阶段二仅用 `scene_native` 数据学习并冻结；阶段三用全新参与者比较 `scene_native` 冻结策略与 `scene_native` 均衡随机。
- 用户已确认阶段一采用“呼吸执行质量非劣 -> 场景—提示语义一致性优效”的有序双门控主要检验链；Gate 1失败时Gate 2只作探索解释。
- 本次确认不自动接受周期容差、`Delta_NI=0.10`、SCCI量表、旧配对功效或104人方案。
- 用户已确认Gate 1唯一主要设备结果采用冻结实时闭环窗口内的有效周期比例 `protocol_fidelity`；只冻结指标角色与计算骨架。
- 用户已确认四模块等权聚合：先分别计算，再以每模块25%的权重形成参与者级Gate 1主要结果；禁止按周期数量直接池化，模块级结果作为预设次要分析。
- 用户已确认四模块完整性规则：任一模块不可评估时，参与者级Gate 1主要结果标记为缺失，禁止使用其余模块重新平均替代完整结果；后续按预注册分析集和敏感性规则处理。
- 用户已确认盲态技术不可评估边界：仅限预注册技术原因；有效记录但执行不符合必须计为失败；判定不得查看提示条件和后续结果。
- 已同步修正离线分析设计中的旧池化公式，改为四模块各25%等权并执行完整性规则。
- 用户已确认模块可评估双门槛：同时满足有效同步呼吸信号覆盖率和模块最低可分析周期数；具体数值留待技术预试冻结。
- 用户已确认周期符合采用“结构硬门 + 模块特定时序容差”；25%阶段误差和20%总周期误差仅作技术预试起点，不直接冻结。
- 用户授权Codex自行判断Gate 1界值；已冻结参与者级四模块等权 `protocol_fidelity` 的绝对比例差 `Delta_NI=0.075`。
- 差值方向为 `scene_native - abstract_pacer`；双侧95%置信区间下界严格大于 `-0.075` 时Gate 1通过，等价于单侧 `alpha=0.025`。
- `0.05`作为更严格敏感性分析；`0.10`只作最宽松情景展示，不得支撑确认性主结论。包内10个百分点为已被取代的历史候选值。
- 技术预试若显示测量不确定性接近或超过7.5个百分点，正式阶段暂停，不得通过放宽界值处理。
- 用户再次授权Codex自行判断；已冻结Gate 1双分析集硬门：完整分析集为主要分析，完整四模块集为支持性分析，两个分析的95%置信区间下界均须严格大于 `-0.075`。
- 任一分析未通过或无法稳定估计，Gate 1不通过，Gate 2降为探索结果；禁止挑选较有利的分析集。点估计方向不一致时执行预注册偏差审计，但不事后改变成功标准。
- 完整四模块集只按盲态技术可评估性形成，不是按执行表现筛选的方案依从集；有效但不符合的周期仍计为失败。
- 新确认门：冻结完整分析集的缺失结果方法，候选为有界多重插补主分析、向不利方向偏移的模式混合敏感性分析和tipping-point边界报告；确认前不冻结功效、阶段一样本量或四人任务包。

## Next-Step Queue

1. 新增项目情况与顶层设计汇总，并接入 M00 导航和 U41 访谈节点。
2. 验证现状/目标分层、已确认/待确认状态、四模块、时间线、数据—结果—结论映射、论文叙事、术语、链接和格式。
3. 仅暂存本任务文件，提交并推送。
4. 下一轮继续 Grill：冻结主论文的因果主张范围，再确定最小比较基准。

## 2026-08-06 Internal Gate Closure And Dispatch Preparation

### Goal

由Codex自行裁定剩余内部设计门，消除旧120秒、交叉设计、PPS、`Delta_NI=0.10`、序列另文和TD/Spout主链冲突，直到项目具备树型任务包分派条件。

### Frozen Research Decisions

- 新增 `00_总控/11_实现冻结基线_v1.0.md`，状态为 `IMPLEMENTATION_DISPATCH_READY`，作为冲突时的最高优先级实现依据。
- 单篇IJHCI采用有序三门：Gate 1双分析集PF非劣、Gate 2通过适用性门的SCCI优效、Gate 3新参与者中冻结策略相对均衡随机的PANAS负性维度优效。
- 完整分析集采用100次有界多重插补；主要分析使用总不利偏移0.075，并报告0至0.15网格和tipping point。完整四模块集不插补。
- 阶段一和阶段三完整结果目标均为每组96、每阶段192；招募按48人块追加，初始上限240，Level C盲态参数可增加，需求超过336则 `NO_GO`。
- SCCI最小关注标准化差为0.50；其8名专家、12至16名认知预试和48名技术预试适用性门必须在正式阶段前通过。
- 阶段二使用带岭惩罚的线性状态—动作价值模型和带20%均匀探索下限的softmax随机策略；不增加固定顺序第三组。
- 技术阈值作为Level C产出而非开发前臆造事实；实现起点、目标值、冻结时点和失败动作均已定义。

### Remaining External Gates

- 伦理路径和批准、设备采购或借用、PANAS版本与许可、Level A/B/C、预注册与正式构建锁定继续阻止相应参与者活动。
- 外部门禁不阻止软件、材料、预试工具和离线流水线任务分派。

### Next Work

同步冻结目标工程模块及接口，生成可独立领取的树型任务包、CSV登记表、依赖与验收矩阵，然后执行整体验证、提交和推送。

### Engineering And Dispatch Result

- `PROJECT_MODULES.md`已重写为M00至M10目标模块，Python会话核心为权威，Unity为独立参与者制品，TD为只读操作台，离线分析从L0重建L5。
- 新增 `21_/06_目标运行接口_v2.md`：可靠控制与ACK、UDP 5005/5006 @ 20Hz、自包含遥测、manifest、Unity四层接口、追加式数据层和正式模式失败关闭。
- UDP 5005/5006已在全局端口注册表登记；可靠控制TCP端口尚未使用，由F-01领取者先登记再实现。
- 产品入口已从旧120秒/8分钟更新为目标25/150/25秒、推荐13分20秒；Unity不再依赖TD或Spout。
- 新增37个1至5人日任务包、依赖CSV、目标接口验收矩阵和无第三方依赖的任务注册验证器。
- 当前仅F-01运行合同、F-02 SCCI材料、F-03 Unity运行壳、F-04 TD只读壳为 `READY`，可由四人并行自主领取。
- README、AGENTS和当前阶段看板已切换到实现冻结与任务领取入口；旧原型运行说明保留并显式标为迁移审计。

### Dispatch Boundary

软件与材料实现现在可以开始。真机任务没有设备证据不能完成；Level A/B/C与正式阶段任务继续标为外部阻塞，不能因任务树存在而越级执行。

## 2026-08-06 Task Package Bidirectional Audit And v2

### Goal

从最终项目完整体反推任务覆盖，再从首波任务正向检查能否装配到Unity独立制品、真实设备链、TD操作台、锁定分析、单篇IJHCI稿件和成果交接；为每个任务补齐领域、过程、验收、证据和国内中文学习资料。

### Audit Decision

- 原37个固定包能启动工程，但不能覆盖M10、预注册与版本锁、阶段一锁定分析、最终报告、资产许可和项目交接。
- Level C及两个正式阶段不能各压缩成一个5人日包；改为每实例最多12人的可重复批次模板，由独立关闭任务汇总QC、平衡、人数、偏离和锁库。
- v2登记51条：48个固定包和3个可重复模板。所有条目工作量为1至5人日，首批仍只有F-01至F-04为`READY`。
- 每个标题带`【领域】`前缀；每包绑定四段过程配置、AC1至AC3、至少两项证据、完成条件和学习资料编号。
- 新增国内中文学习资料索引，链接已于2026-08-06逐条做可访问性检查；领取时仍需记录实际课程和访问日期。

### Composition Result

- 自动校验确认依赖无环，所有51条输出均可沿下游依赖到达最终交接任务W-04。
- 反向覆盖矩阵把十类最终成果映射到直接任务和完成判据。
- 原v1任务包标记`SUPERSEDED`，v2手册由CSV确定性生成，避免人读文档与状态登记漂移。

### Boundary

本轮只重构任务分派体系，不关闭任何真机、Level、预注册、锁库、论文或外部成果门。学习资料不能替代任务验收。

## 2026-08-06 Math-Modeling PDF Briefs

### Goal

使用数学建模论文生产流水线，将当前实现冻结基线和v2任务体系整理为三份可直接分发的PDF：项目目标与可行性、固定任务概要、项目设计与实验流程。

### Scope And Expected Evidence

- 三份文档统一使用A4中文数学建模论文结构，包含摘要、关键词、编号章节、图表或公式、结论与参考文献。
- 固定任务概要必须覆盖48个固定任务，并单列3个可重复批次模板，不能把外部门禁写成已完成。
- 项目设计文档必须保持Unity独立参与者制品、Python会话核心权威、TouchDesigner只读操作台和三阶段研究设计。
- 构建后执行逐页文本、页面尺寸、关键章节、术语边界、渲染图像和项目测试验证。

### Output

- `output/pdf/01_项目目标介绍与可行性论证.pdf`
- `output/pdf/02_固定任务概要.pdf`
- `output/pdf/03_项目设计简述与实验流程.pdf`

### Boundary

这些PDF是顶层设计和任务分发制品，不代表设备、Level、正式阶段、统计结果、投稿或外部认可已经完成。

## 2026-08-06 IJHCI Contribution Viability Audit

### Decision

- Overall: `CONDITIONAL_GO`, design-maturity score 73/100, not an acceptance probability.
- Primary contribution: scene-native breathing guidance can stand only as a cross-structure interaction-representation framework with an information-matched comparator, ordered functional and representational gates, and transferable design knowledge.
- Secondary contribution: explainable sequence orchestration remains `REVISE_REQUIRED` until a frozen policy is independently compared with balanced random ordering in new participants and supported by audit and ablation evidence.
- One-paper coherence: unify both through within-module representation and between-module orchestration; keep explicit primary-secondary hierarchy.

### Immediate Design Consequence

No additional participant arm is required. Add construct closure, comparator matching audit, process evidence, low-cost policy ablations, and explicit mapping rules and failure modes before preregistration and manuscript lock.

## 2026-08-06 Multidimensional Topic Upgrade

### Goal

Upgrade the IJHCI topic without adding participant conditions or diluting the single-paper hierarchy. Push the contribution audit into design, implementation, analysis, accessibility, open-science and task-acceptance authorities.

### Frozen Upgrade

- Keep the four fixed composite modules, three stages, Gate 1-3, sample anchors, real-device roles and Unity/Python/TD architecture unchanged.
- Add a four-construct evidence model, cross-module four-layer representation grammar, functional-equivalence comparator audit, process evidence, module error taxonomy, strategy ablation/support/stability audit, Unity accessibility baseline and openness statement.
- Use within-module representation as the primary contribution and between-module orchestration as a conditional secondary contribution.
- Add no fifth scene, fifth breathing structure, extra participant arm, high-capacity model or extra device to the current critical path.

### Task Impact

Reuse the existing 48 fixed tasks and three templates. Strengthen 16 task packages and enforce their upgrade markers in the registry validator; regenerate the deterministic handbook after registry edits.

## 2026-08-06 Independent IJHCI Reviewer Attack And Protocol v1.1

### Goal

Use three isolated, read-only reviewer roles to attack the same project snapshot from HCI contribution, experimental/statistical, and engineering/reproducibility perspectives; adjudicate the shared objections and upgrade every active execution authority without presenting the exercise as external human review.

### Reviewer Decision

- Overall decision: `REJECT_AND_RESUBMIT_DESIGN`.
- Evidence status: `PLANNED_NOT_OBSERVED`.
- The previous `CONDITIONAL_GO` score is superseded for execution because it underweighted construct circularity, policy support, runtime evidence and study capacity.
- SCCI is a manipulation check. Gate 2 now also requires condition-neutral four-layer comprehension noninferiority and mental-effort noninferiority.
- Stage 1 identifies the complete cue-representation package, not an isolated weather, breathing structure or visual mechanism.
- The four-layer grammar is conditional on an independent reconstruction task; failure downgrades it to a four-scene design pattern.
- Sequence orchestration is a deployment extension. It enters Stage 3 only after participant-grouped cross-fitting, OPE, ESS and action-support gates; otherwise the uniform policy remains and the priority claim is removed.

### Frozen Execution Changes

- Added `00_总控/13_IJHCI独立审稿攻击与升级裁定_v1.1.md` and machine authority `00_总控/protocol_authority_v1.1.json`.
- Added an executable protocol firewall in `99_验证与清单/validate_protocol_authority_v1_1.py`; marked four earlier control documents `SUPERSEDED_FOR_EXECUTION`.
- Rewrote active Stage 1-3, Level C, product, runtime, offline-analysis, policy, paper and reporting authorities around one-participation parallel groups and exact questionnaire timing.
- Replaced analyzable-cycle PF denominators with expected opportunities and explicit `COMPLIANT`, `NONCOMPLIANT` and `TECH_UNOBSERVABLE` states.
- Froze participant-level randomization, list custody and salted repeat-participation deduplication; Stage 3 uses the same `scene_native` build and estimates the deployed policy including fallback.
- Rebudgeted 528 maximum sessions at 55-70 station minutes to 484-616 station-hours and added a mandatory two-week throughput rehearsal.
- Strengthened 20 existing task packages while preserving 48 fixed packages, three batch templates and exactly F-01 through F-04 as `READY`.
- Rebuilt the three math-modeling-style PDF briefs from the v1.1 source authorities.

### Next Hard Gates

1. Run the closest-work review and independent four-layer reconstruction task.
2. Build the real-device Unity/Python/TD baseline and obtain LIVE_E2E, external display latency, multi-hour stability and clean-machine evidence.
3. Complete Level A/B/C, Gate 2 tool calibration, sample-size Monte Carlo and the two-week throughput rehearsal before any formal participant stage.

### Boundary

Repository consistency is verified; research effects, strategy superiority, external review and publication acceptance remain unobserved.

## 2026-08-06 Complete F-02 Candidate Measurement Package

### Goal

Audit the supplied Deep Research output against F-02 AC1-AC3, reconstruct any missing repository-owned artifact, and advance only dependency states justified by accessible evidence.

### Evidence And Decision

- The supplied `deep-research-report.md` is a summary, not the linked full package; its claimed artifact path and internal session references are not usable project evidence.
- Rebuilt a self-contained `v0.9-candidate` package with the construct graph, four primary SCCI items, eight condition-neutral comprehension items and answer key, one mental-effort item, a measured five-minute target, Level A/B instruments, ordinal item audit, failure rules and R-01/W-01 interfaces.
- Completed an independent AC review and added a dedicated validator. F-02 is `DONE` only at candidate-material scope; Level A/B/C, U1/U5 and Gate 2 remain open.
- Extended the registry lifecycle to validate `DONE` and dependency-derived `READY`. F-02 completion unlocks G-01 and R-01; the current READY set is F-01, F-03, F-04, G-01 and R-01.

### Next Hard Gates

1. R-01 must provide information-equivalent two-condition fixtures and visual-confound evidence.
2. Level A must complete expert content and construct-boundary review.
3. Level B must run two-condition cognitive interviews, item-function auditing and measured questionnaire timing before the tool or margins can freeze.

### Boundary

No expert judgment, interview result, condition effect, noninferiority margin, Gate 2 result or publication result is claimed by this task.

## 2026-08-06 Complete R-01 Candidate Representation Package

### Goal

Audit the supplied R-01 Deep Research package, replace unusable citations, make its Schema evidence executable, and advance only dependencies justified by the accepted candidate design.

### Evidence And Decision

- The supplied `deep-research-report (3).md` is a complete approximately 70 KB candidate package, unlike the earlier F-02 summary.
- Removed 42 internal session citations, added repository-relative authority links, retained stable DOI or official links, and recorded source SHA-256 `66C78634...8AC0D31`.
- Corrected one material omission: the current authority freezes storm as `3-3-3-3`; the imported report had called it unspecified.
- Extracted a Draft 2020-12 Schema, two condition-valid fixtures, four targeted invalid fixtures and one comprehension-truth fixture. Metaschema validation passed; both valid fixtures passed; all four invalid fixtures were rejected.
- Independent AC review accepts R-01 at candidate-design scope. R-01 is `DONE`, W-01 is newly `READY`, and all other R-01 consumers remain blocked by their additional dependencies.

### Next Hard Gates

1. W-01 must attack the closest 2015-2026 work and keep novelty claims conditional.
2. U-07 must measure the six confounds from real Unity renders before formal ranges can freeze.
3. Q-01 and later Levels must test reconstruction, layer discriminability and neutral comprehension with independent evidence.

### Boundary

The accepted package does not establish Unity implementation, team dual sign-off, transferable-framework validity, Level results, Gate results or publication novelty.

## 2026-08-06 Remove Root CLAUDE.md

- User explicitly authorized deletion of the modified root `CLAUDE.md`.
- No active Markdown link depends on the file; remaining mentions are historical records.
- `AGENTS.md` remains the project instruction authority.
- Other pre-existing deletions and untracked files remain outside this task.

## 2026-08-06 Complete W-01 Closest-Work Candidate Package

### Goal

Audit the supplied W-01 Deep Research package, preserve only reproducible evidence, deliver the closest-work matrix and one-paper IJHCI skeleton, and advance task state without claiming that novelty or study effects are established.

### Evidence And Decision

- Imported `deep-research-report (2).md` after confirming SHA-256 `5856C9C...18CD7E`.
- Removed 52 GPT internal citation markers, normalized the evidence cutoff to 2026-08-06 and Asia/Shanghai, fixed the Adaptive Biofeedback year to 2016, and replaced the incomplete Heart Garden author field with the verified author list.
- Extracted 13 search-log rows, 15 seven-axis closest-work records, six claim-refutation records, 15 BibTeX entries and a 15-row DOI identity audit.
- Independent AC review accepts W-01 only at candidate-package scope. The task is `DONE`, but novelty remains `REVISE_REQUIRED` and project evidence remains `PLANNED_NOT_OBSERVED`.
- The current task state is `DONE={F-02,R-01,W-01}` and `READY={F-01,F-03,F-04,G-01}`. W-02 remains blocked by A-04.

### Next Hard Gates

1. Export and archive native ACM Digital Library plus Scopus or Web of Science results, exact counts, deduplication and exclusion reasons.
2. Complete independent two-person screening and high-threat full-text coding, especially `Breathing a Lullaby`.
3. Use Q-01 reconstruction evidence to decide whether the contribution can retain a cross-structure grammar claim.
4. Keep the sequence extension outside the title, abstract and primary contribution unless both U6 and Gate 3 pass.

### Boundary

W-01 completion does not establish comprehensive search coverage, external human review, a transferable framework, any Gate result, any observed effect or publication acceptance.

## 2026-08-06 Freeze Four-Person Team Tool Baseline

### Goal

Define one versioned common environment for all four members, add only role-owned heavy tools, and make version drift detectable before task pickup.

### Evidence And Decision

- Froze the common baseline at Windows 11 x64 build 26100+, PowerShell 7.6.4, Git 2.54.0.windows.1, Git LFS 3.7.1, OpenSSH 9.5p2, Python 3.14.4, pip 26.1.1, pytest 9.0.3, VS Code 1.131.0 and Zotero 9.0.6.
- Added role profiles for design, Unity, Python/data and experiment/TD/governance. Unity is fixed at 6000.4.9f1 revision f7258d6eebbe; TouchDesigner is fixed at 2025.32820.
- Added a nine-package Python direct dependency baseline and cross-checked the Unity package versions and resolved Unity MCP commit against the repository locks.
- Added a machine-readable JSON authority and a validator with authority-only and per-role local inspection modes.
- The coordinator machine matches every tested common and role-specific version except Zotero 9.0.6, which is not installed. TD MCP service dependencies remain optional and not ready.

### Next Hard Gates

1. Install Zotero 9.0.6 on all four machines and grant access to the same shared library.
2. Run the role-specific validator on each machine and archive the output with the first claimed task.
3. Replace the Unity MCP `#main` source with an immutable commit reference before the first package mutation.
4. Produce a complete transitive Python lock and clean-environment reconstruction before LIVE_E2E.

### Boundary

Tool registration and matching versions do not establish implementation, real-device readiness, independent reproduction, Level evidence or Gate results.

## 2026-08-06 Correct Team Tool Baseline Scope

### Goal

Apply the user's clarification that Unity, TouchDesigner and the full frozen Python data-processing stack are required on every team member's machine; roles divide ownership, not tool availability.

### Evidence And Decision

- Supersedes the preceding statement that heavy tools were added by role.
- Added Unity 6000.4.9f1 revision f7258d6eebbe, TouchDesigner 2025.32820 and the nine pinned Python direct dependencies to the common tool set.
- Kept Unity MCP, TouchDesigner MCP and Codex Desktop outside the shared installation requirement because they are automation aids rather than core project production tools.
- Changed role profiles to ownership labels with no required-tool additions; every local role mode now validates the same complete installation set.

### Next Hard Gates

1. Install Zotero 9.0.6 on the coordinator machine and all other team machines.
2. Run the corrected validator under each assignee's role label and archive the output with the first claimed task.
3. Audit the other three machines; the coordinator result cannot stand in for their evidence.

### Boundary

Having the same tools installed does not prove that every member can perform every role's acceptance workflow; capability evidence remains task-specific.

## 2026-08-06 Narrow Zotero Installation Scope

### Goal

Require local Zotero only where reference curation and paper evidence are owned, while preserving shared-library access for all four members.

### Evidence And Decision

- Supersedes the earlier all-machine Zotero installation requirement.
- Design and experiment/TD/governance roles must install Zotero 9.0.6; the latter owns paper evidence governance.
- Unity and Python/data roles may use Zotero Web Library and are not blocked by a missing local executable.
- All four members still need a manual shared-library access check because repository validation cannot inspect private group permissions.

### Next Hard Gates

1. Install Zotero 9.0.6 on the design and paper-evidence-governance machines.
2. Grant all four accounts at least read access and archive a redacted access check with each person's first task.
3. Assign write or administrative rights only to members whose curation duties require them.

### Boundary

Passing the local tool validator does not establish access to the private shared library; that remains a separate human-verifiable permission gate.

## 2026-08-06 Generate Individually Dispatchable READY Task Packages

### Goal

Give every currently unlocked task its own dispatch directory containing a complete task brief, involved-file manifest, necessary input snapshots and machine-verifiable provenance, then make this mandatory whenever the READY set changes.

### Evidence And Decision

- Generated separate packages for F-01, F-03, F-04 and G-01 from the registry authority.
- Each package contains `TASK.md`, `FILES.md`, `package_manifest.json`, blank claim/completion fields, acceptance checkboxes, working paths and hashed input snapshots.
- Curated 48 necessary input snapshots across the four packages; Unity and TouchDesigner project roots remain working paths rather than copied caches or generated directories.
- Added a READY-to-file mapping, deterministic renderer and validator. The main 51-entry task validator now also rejects missing or mismatched independent packages.
- Added the workflow as a project habit in `AGENTS.md`; future READY transitions must update the mapping, regenerate packages and pass both validators before distribution.

### Next Hard Gates

1. Each assignee fills the claim fields before implementation and works only in the listed authority paths.
2. When a task changes state, regenerate the directory so stale READY packages cannot remain distributable.
3. Input snapshots are review aids; source changes require a regenerated hash manifest.

### Boundary

Package generation does not claim that F-01, F-03, F-04 or G-01 has started or completed. Relative links inside copied source snapshots may still assume the original source directory; `FILES.md` links back to those authority files.

## 2026-08-07 Implement F-01 Runtime Contract Technical Closure

### Goal

Complete the F-01 technical scope across the project architecture without implementing downstream session, storage, Unity or TouchDesigner tasks, and preserve the mandatory second-person review boundary.

### Evidence And Decision

- Added the v2.1 Python contract validator, Draft 2020-12 combined Schema, six message families, 11 hashed fixtures, migration guide and AC record.
- Formal manifests require PLUX respiBAN and Polar H10 sources, a known Unity build and no Mock input. Missing fields, wrong versions, retired fields, duplicate controls and stale sequences fail closed; unknown compatible fields are filtered out.
- Reserved TCP 5010 for reliable control, ACK, render receipts and TD requests after confirming no active listener. UDP 5005/5006 retain read-only TD and Unity telemetry roles.
- Preserved v1.2 UDP and CSV code as `LEGACY_DEV_ONLY`; no real-device, session-core, Unity or TD runtime claim was made.
- F-01 remains `READY` with claimant and branch recorded because second-person review is still pending. P-01, P-02, G-02, U-01 and T-01 remain dependency-blocked.

### Next Hard Gate

A non-implementing team member must execute the review checklist in `02-技术研发/05-通信协议/F-01_技术验收记录.md`, record findings and sign the interface before F-01 may become `DONE` and unlock downstream tasks.

### Boundary

Contract and fixture completion does not establish a listening TCP service, persistent L0/L1 records, Unity or TD consumers, real-device LIVE_E2E, Level evidence or any Gate result.

## 2026-08-07 Remediate F-01 Independent Review Findings

### Goal

Close every reproducible F-01 contract finding while preserving the real-team second-review gate.

### Evidence And Decision

- Four isolated review rounds found and drove fixes for Schema/Python drift, EOL-sensitive hashes, missing rejection audit records, malformed enum exceptions, unexecuted Draft 2020-12 validation, source-mode provenance, stage-one probability, fallback consistency, audit ordering and arbitrary-precision integers.
- The contract suite now executes the Schema and reference runtime against fixtures, required-field/type mutations and semantic counterexamples. A PowerShell consumer independently reads baseline and forward-compatible telemetry.
- The final isolated model review found no P0-P2 issue after deterministic READY package regeneration and returned `PASS_FOR_MODEL_INDEPENDENT_REVIEW`.
- F-01 remains `READY`; model review is evidence only and cannot substitute for a real non-implementing team member's signature.

### Next Hard Gate

A named team member must review the exact pushed commit, record commands, findings and identity in the F-01 acceptance record, then approve the governance-only transition to `DONE`.

### Boundary

This closes the implemented contract's model-review loop only. It does not complete P-01, P-02, Unity, TouchDesigner, real-device integration or a full-system run.

## 2026-08-08 Project-Wide Defect Remediation

### Goal

Land repository-safe fixes from the independent audit without fabricating Unity completion, external approval, participant evidence or LIVE_E2E.

### Implemented

- Preserved timestamped native-rate ECG batches through the 10 Hz coordination frame; removed averaged-ECG interpolation and neutral missing-channel defaults.
- Made invalid/warmup windows non-emitting; corrected trend state order, mock latency, fatal error propagation, CSV schema drift and asynchronous device shutdown.
- Added runtime-contract cross-field invariants and negative tests; root pytest now excludes the TD vendor environment and passes as one canonical entry.
- Added a Unity formal-build preprocessor gate. Its current expected result is `FORMAL_SCENES_MISSING`; this prevents the legacy SampleScene/v1.2 prototype from being published as formal v2.1.
- Disabled TD mutation controls by default unless `SRP_TD_DEV_CONTROL=1` is explicitly set for development.
- Moved F-01 to `IN_REVIEW`, distinguished review packages from claimable READY tasks, added current v1.1 authority to every dispatch package and regenerated 74 snapshots.
- Marked all 20 legacy participant-material Markdown files as superseded/non-distributable; isolated the historical novelty and reference entries; replaced non-authorized acquisition links and added a fail-closed provenance validator.
- Built a Git-index-only review snapshot. Its first clean checkout exposed line-ending-sensitive hashes for `.sha256`, `.ps1` and numbered `.gitattributes` inputs; the shared canonicalization policy and regression test now cover them, and the rerun passed 100 tests plus strict package validation.

### Open Hard Gates

- F-01 still requires a named non-implementing team member; F-03, F-04 and G-01 remain READY.
- Unity lacks formal scenes/controller and tests; real device adapters and LIVE_E2E remain absent.
- Reference provenance validation intentionally remains red until the inventory is rebuilt with identity, hash, source, access basis and asset-role fields.
- External approvals, scale permission, Level A/B/C, Monte Carlo, throughput rehearsal, preregistration and locked analysis cannot be closed by repository edits.

## 2026-08-11 Prepare F-01 Human Second-Review Report

### Goal

Provide a self-contained report that lets a real non-implementing team member review F-01 against implementation commit `6c27c94a53c3eaa57d77b12a74626eb7442bfc0e` without pre-filling or fabricating the human conclusion.

### Evidence And Decision

- Added `02-技术研发/05-通信协议/F-01_第二人审核报告_待签署.md` with fixed scope, authority links, repeatable commands, AC checklists, findings table and blank identity/conclusion fields.
- Fresh verification produced 49 contract passes, 100 project passes, a passing PowerShell consumer, and passing registry, package and protocol validators.
- F-01 remains `IN_REVIEW`; the report explicitly separates F-01 approval from the broader 112-file implementation commit and from downstream runtime claims.

### Next Hard Gate

A named team member must independently execute or witness the listed checks, record findings and sign the report. Only a human `PASS` permits a separate governance commit that moves F-01 to `DONE` and recalculates newly READY tasks.

## 2026-08-12 Close F-01 Signoff And Unlock G-02/P-01/P-02

### Goal

Record the named second-person F-01 acceptance without overstating how evidence was obtained, migrate every current governance surface, generate all newly READY packages and freeze a decision-complete G-02 plan.

### Evidence And Decision

- 傅钧烨 confirmed acceptance as team director and independent second reviewer, based on witnessing the existing verification results and reviewing the fixed files; the report explicitly states that the reviewer did not personally rerun the commands.
- Acceptance commit `58c9e41871214351a0fe96a413dfbc34d482ed4a` binds the completed report to implementation commit `6c27c94a53c3eaa57d77b12a74626eb7442bfc0e`.
- F-01 moved from `IN_REVIEW` to `DONE`; G-02, P-01 and P-02 moved from `WAIT_DEP` to `READY`; F-03, F-04 and G-01 remain `READY`.
- The dispatch set is now exactly F-03, F-04, G-01, G-02, P-01 and P-02. U-01 and T-01 retain other unmet dependencies; D-01 and D-02 retain external and upstream gates.
- Added `G-02_数据治理实施计划_v1.0.md`, freezing L0-L5 classification, phone-only HMAC deduplication, credential custody, store separation, fail-closed APIs, backup recovery, tracked Unity asset licensing and downstream contracts. G-02 remains `READY`; no implementation claim was made.

### Verification

- F-01 contract suite: `49 passed in 1.50s`; root regression: `100 passed in 13.82s`.
- Registry validator: 51 entries; `DONE=F-01,F-02,R-01,W-01`; six expected READY tasks; no `IN_REVIEW` task.
- Indexed dispatch validator: six packages, 77 snapshots; protocol authority and PowerShell non-Python consumer passed.
- Fixed-task PDF: eight A4 pages, text checks passed, SHA-256 `E23243D839DF47BFBC94688B961DD12FA60C12ABE1EA97991E5AD0978B21561E`; all pages were rendered and visually inspected without clipping or overlap.

### Open Hard Gates

- F-01 completion covers the runtime contract only. P-01, P-02, Unity, TouchDesigner, real-device integration and a full-system run remain separate tasks.
- G-02 is planned and dispatchable, not implemented. Formal contact collection remains closed until the dedicated account, encrypted governance volume, credential, retention approval and access evidence exist.
- The project-level novelty state remains `REVISE_REQUIRED`, and the independent-review project state remains `REJECT_AND_RESUBMIT_DESIGN`.

## 2026-08-12 Implement G-02 Data Governance Candidate

### Goal

Implement the frozen G-02 data-governance design, prove the synthetic technical loop and fail-closed release behavior, then move the task to human second review without claiming formal-machine readiness.

### Evidence And Decision

- Implementation commit `befbdb698ef5cbeb6061315a4c912abdde4e6b08` adds L0-L5 authority, strict E.164 normalization, domain-separated HMAC deduplication, isolated identity mapping, append-only audit chaining, authenticated backup recovery, manifest privacy linting and downstream contracts.
- The cross-stage state machine covers Level B, Level C, stage 1 and stage 3, including concurrent reservation, release before exposure and permanent blocking after exposure.
- Unity now has a Git-derived 179-item inventory, license ledger and synchronous formal-build gate. Three unresolved asset groups retain owners, deadlines and exclusion plans and continue to block release.
- G-02 tests report `107 passed`; the synthetic rehearsal and repository privacy gate pass. The formal environment gate reports six missing machine controls, and Unity exits with the expected asset-license block after successful C# compilation.
- G-02 moves from `READY` to `IN_REVIEW`. The READY set becomes exactly F-03, F-04, G-01, P-01 and P-02; no G-02-dependent downstream task is newly unlocked.

### Open Hard Gates

- A dedicated Windows account, separate encrypted governance and backup roots, Credential Manager secret, sealed recovery evidence and institution-approved retention period remain required.
- The three Unity asset groups must be cleared or excluded before publication.
- A real team member independent of the implementation must review the fixed commit and sign `G-02_第二人审核报告_待签署.md`.

## 2026-08-13 Implement P-01 SessionCore Candidate

### Goal

Implement the v2.1 fixed-sequence session authority and minimum Python loopback transport, integrate its contracts with G-02/P-02/X-01 and Unity boundaries, then move P-01 to human second review without claiming downstream runtime completion.

### Evidence And Decision

- Implementation commit `8063afc7053a79a0d27fe8fc94159dbc5fc9a9e0` adds deterministic `SessionCore`, fixed `SequenceProvider`, formal gates, session-event schema, protocol configuration, TCP 5010 control delivery, UDP 5005/5006 validated mirroring and a four-module golden trace.
- The golden trace completes storm, heat, snow and fade once each in 800 seconds with trace hash `sha256:c163f211396dc979fa9f63ce25a8984cc3a4f2010ba71d8711d3223abf7c4491`.
- Independent model review found five P1-P2 candidates. Abort delivery/disconnect, semantic ACK failure and local-clock 20 Hz enforcement were repaired; conservative exposure and duplicate-request rejection were confirmed as intended. The second review returned `PASS_FOR_MODEL_INDEPENDENT_REVIEW` with no open P0-P2.
- P-01 moves from `READY` to `IN_REVIEW` at six person-days. F-03 is explicitly a Python-controlled render mirror, not a second session authority. The claimable set becomes F-03, F-04, G-01 and P-02; G-02 and P-01 remain review-only.

### Open Hard Gates

- A real non-implementing team member must review and sign the fixed P-01 implementation commit before `DONE`.
- P-02 durable append storage, X-01 randomization authority, Unity/TD consumers, real devices and `LIVE_E2E` remain separate open tasks.
- Stage 3 frozen-policy ordering is blocked with `ADAPTIVE_SEQUENCE_REQUIRES_V2_2`; v2.1 does not reinterpret `weather_sequence` as a fallback sequence.

## 2026-08-16 Implement P-02 Durable Session Store Candidate

### Goal

Implement append-only manifest/L0/L1 storage and deterministic P-01 replay, preserve interrupted bytes without resuming experience progress, and move P-02 to human second review without claiming formal runtime closure.

### Evidence And Decision

- Implementation commit `3d740e99118d6a76993156f26bdf673144429025` adds exclusive manifest storage, segmented canonical JSONL hash chains, checkpoints, seal scopes, interruption recovery, P-01 recording adapters, telemetry store-before-send and side-effect-free replay.
- Formal capability requires a repository-external root, configured system account and role, G-02 authorization, encryption and minimum ACL checks. Development archives cannot self-declare formal capability.
- The P-01 golden archive preserves 19 controls, 19 ACKs, 12 render receipts, 54 session events and 46 committed operations. The 800-second stress candidate records 320000 PLUX samples, 104000 Polar samples and 16000 L1 frames with valid integrity.
- Independent model review required four rounds. All four P1 and two P2 findings were closed; final status is `PASS_FOR_MODEL_INDEPENDENT_REVIEW`.
- P-02 moves from `READY` to `IN_REVIEW`. The READY set becomes exactly F-03, F-04 and G-01; D-01/D-02 retain device gates and A-01 still waits for S-02.

### Open Hard Gates

- A real non-implementing team member must review and sign the fixed P-02 implementation commit before `DONE`.
- Formal-machine encryption, ACL, account and integrated runtime evidence remain required.
- Real device adapters, Unity/TD consumers, X-01, A-01 and `LIVE_E2E` remain separate tasks.

## 2026-08-16 Fresh Independent Agent Audit Of IN_REVIEW Tasks

### Goal

Run separate read-only Agent reviews against the fixed G-02, P-01 and P-02 implementation commits, preserving human-signature authority and current task states.

### Evidence And Decision

- Three independent Agents reviewed G-02 `befbdb698ef5cbeb6061315a4c912abdde4e6b08`, P-01 `8063afc7053a79a0d27fe8fc94159dbc5fc9a9e0` and P-02 `3d740e99118d6a76993156f26bdf673144429025`.
- All three returned `REVIEW_FINDINGS_OPEN`: 0 P0, 4 P1, 4 P2 and 2 P3 findings.
- New counterexamples cover credential overwrite, embedded contact leakage, unconfirmed completion, premature ACK, receipt mismatch, envelope mutation, seal/recovery races and invalid memory-trend evidence.
- The detailed evidence is recorded in `03-测试与实验/IN_REVIEW_Agent独立审核报告_2026-08-16.md`.
- G-02, P-01 and P-02 remain `IN_REVIEW`; pending human second-review reports were not edited or signed.

### Next Queue

- Close P1 findings first with regression tests, then P2 and P3 findings.
- Freeze new implementation commits and rerun independent Agents before requesting human second review.
- Do not reuse earlier model-pass statements as current closure evidence.

## 2026-08-16 P1-P2-P3快速修复

- P-01固定提交`03d7426`，专项`98 passed`，独立Agent `01a008fa-b83f-7982-ab82-b8fde66b8c93`返回`PASS_FOR_MODEL_INDEPENDENT_REVIEW`。
- P-02固定提交`03d7426`，专项`68 passed`，独立Agent `01a00910-6889-78e0-94d4-246e2409f328`返回`PASS_FOR_MODEL_INDEPENDENT_REVIEW`。
- G-02专项`138 passed`；独立Agent `01a00914-d4c5-7fc1-8966-a400aaccba66`返回`PASS_FOR_MODEL_INDEPENDENT_REVIEW`，51项注册表及6包/182快照校验通过。
- 三项继续保持`IN_REVIEW`，真实团队第二人签署、正式专机与Unity资产门不因模型复审通过而关闭。

## 2026-08-17 Unity实验环境渐进搭建与任务协调

### 目标

在不抢跑Unity场景实现的前提下，重新组织Unity任务依赖和验收证据，使团队从可复现环境逐步装配到完整参与者制品和全链路环境。

### 裁定与证据

- 冻结`E0 F-03 -> E1 U-01/U-02 -> E2 U-03 -> E3 U-04/U-05/U-06/U-07 -> E4 U-08 -> E5 I-01`路线。
- F-03扩展为精确Unity/包锁环境、测试架、P-01 golden驱动会话壳、无TD无Spout开发构建和正式门负路径，仍保持`READY`。
- U-01新增P-01依赖；U-03成为首个风暴200秒纵向切片；其余场景在U-03后并行；I-01新增P-02依赖。
- 资产盘点可与E0至E3并行，但未知、未跟踪或未登记资产继续阻断U-08正式候选。
- 注册表51项和6个分发包通过验证，F-03包增加协调计划后共有183个快照；根回归`404 passed`。
- 固定任务概要重建为8页，SHA-256为`1C3453527C839C29177E093E546AE4C1895A97207115B3CA50EC28AE27E5D606`，逐页检查无截断、重叠或乱码。

### 边界与下一步

- 本轮只完成任务协调和分发制品，不声称Unity工程已编译、场景已按新接口完成或正式构建已放行。
- 下一可执行Unity包仅为F-03；U-01必须等待P-01签收，U-08必须通过G-02资产门，I-01必须等待P-02及其他前置。
- 默认`python`当前指向缺少pytest的3.14.5；验证改用可发现且带pytest 9.0.3的`py -3.14`，未安装新依赖。

## 2026-08-18 Unity场景设计流程订正与任务包落盘

### 目标

废止“先做指定天气纵向切片再补设计”的当前执行口径，按游戏场景设计流程重新建立Unity前期设计、技术支撑、灰盒、纵向切片和批量生产的依赖树，并生成可独立领取的首个前期设计包。

### 裁定与证据

- 新增V-01至V-05五个固定任务，依次覆盖研究体验契约与完整旅程、天气概念与呼吸提示专项原型、四层视听映射与资产来源、完整分镜与真实时长声音预演、四模块全旅程灰盒与形成性回退门。
- F-03收缩为可复现工程与测试构建基线；U-01负责可靠控制技术探针；U-02负责SceneAdapter；U-03改为由V-02风险矩阵选择最高风险天气，不再预设具体天气。
- Unity设计主线冻结为`V-01 -> V-02 -> V-03 -> V-04 -> V-05 -> U-03 -> U-04/U-05/U-06/U-07 -> U-08 -> I-01`，F-03、U-01和U-02作为技术支撑在相应门前汇合。
- 注册表现含56项，其中53个固定任务、3个模板；当前`READY`固定为F-03、F-04、G-01、V-01，G-02、P-01、P-02保持`IN_REVIEW`。
- 独立任务包确定性重生成通过，共7包、186个输入快照；新增V-01包并刷新F-03边界。
- 固定任务概要重建为9页，SHA-256为`54483B4EF13BEE3F485EB411B4567CFBBFAC5128CD00D3919DEFE73C1D35D4CB`，逐页检查无裁切、重叠、孤立表头或乱码。
- 全仓回归`404 passed in 22.62s`；协议权威、注册表、独立任务包、禁用表述和暂存差异检查均通过。

### 边界与下一步

- 本轮只完成设计流程、任务依赖、领取包和说明制品，不声称Unity场景、灰盒、测试构建或正式候选已经完成。
- V-01可以与F-03并行领取；V-02至V-05必须依赖前序证据逐级解锁，禁止在V-05回退门前批量制作四个天气。
- G-02、P-01、P-02的真实团队第二人签收、Unity资产许可、真实设备和`LIVE_E2E`仍是后续硬门。

## 2026-08-18 V-01 研究体验契约与完整旅程

### 目标

执行 Unity 从头设计的第一步，在任何天气、美术或声音定案之前，冻结研究体验、系统权威、完整旅程、证据路径和设计主张边界，为 V-02 提供不依赖旧 Unity 场景的起点。

### 已完成

- 建立26个冻结或版本化约束、15个开放创作问题、12个旅程节点和10条结构化主张。
- 明确第一模块只来自 Python manifest；前量表与后量表均不由 Unity 读取，核心体验不要求参与者进行手部操作。
- 明确两种条件是覆盖四模块、三个固定段和四层真值的完整表示包；第三阶段使用同一`scene_native`构建，只比较顺序策略。
- 提交`2854223`形成初始候选；独立 Agent `01a012e3-ebfb-7fc0-8747-7d492e8aa612`发现3个P2和1个P3校验缺口；提交`293720f`补齐跨总控、TouchDesigner只读、条件覆盖和结构化主张校验。
- 第二轮独立复审返回`PASS_NO_OPEN_P1_P3`。模型结论不替代真实团队第二人签收。
- V-01迁移到`IN_REVIEW`，V-02继续`WAIT_DEP`；当前可领取集合为F-03、F-04、G-01。

### 验证与边界

- 根回归`404 passed in 17.63s`；协议权威、V-01契约、任务注册表和独立任务包均通过。
- 四类负向篡改覆盖TouchDesigner越权、条件单位漂移、完整包缺模块和主张状态越界，均被校验器拒绝。
- 固定任务概要为9页，SHA-256为`2E314D87D72AF274228DF0F67C47D81DA7B39E4D9C0EFEE87270377DEA426585`，逐页及重点页检查无裁切、重叠或状态冲突。
- 本步未操作 Unity Editor，未选择最终天气、抽象提示、叙事、声音或资产，未形成构建、真实设备链、`LIVE_E2E`或正式参与者结果。

### 下一步

- 真实团队第二人审阅`V-01_技术验收记录_待第二人复核.md`；只有签收为`DONE`后才将V-02改为`READY`。
- F-03可以继续独立建立Unity工程、测试和开发构建基线，但不得提前冻结天气方案。

## 2026-08-18 V-01签收闭环与V-02解锁

### 目标

把傅钧烨对固定实现提交`293720f40126e2892b585c78fe7908518f40d4ad`的真实团队第二人`PASS`结论独立落盘，随后将V-01迁移为`DONE`、将V-02迁移为`READY`，并恢复逐节点设计核对入口。

### 已完成

- 签收提交`339b94fb0a5e4527032cf59a835d6691419c8a76`只记录审核人、角色、复核方式、对象、结论、日期和不扩大范围。
- 后续治理增量回填签收提交SHA，并将验收记录重命名为`V-01_技术验收记录_已签署.md`。
- 注册表迁移为`V-01=DONE`、`V-02=READY`；G-02、P-01、P-02保持`IN_REVIEW`，F-03、F-04、G-01保持`READY`。
- `READY`任务必须未领取，因此V-02领取人、分支和复核人字段保持为空；当前对话开始逐节点决策核对，不把讨论开始误写成已完成实现。
- 独立任务包移除V-01并加入V-02，确定性重生成后为7包、196个输入快照。

### 验证与边界

- 根回归`404 passed in 18.75s`；协议权威、V-01契约、任务注册表和独立任务包校验均通过。
- 固定任务概要PDF为9页，SHA-256为`36F393B287D01F42B4D875BDF39FF1DFB4DBFFF882B7131A339EDC4302D23041`，逐页检查无裁切、重叠或乱码。
- V-01签收只关闭研究体验契约与完整旅程设计门；Unity运行、构建、真实设备链和`LIVE_E2E`仍由下游任务提供证据。
- 下一步进入V-02节点1，只确认设计对象、功能位置、用户可见概念和稳定技术ID的术语边界，确认后立即写入V-02上下文。

## 2026-08-20 V-02场景确认收口

### 目标

按用户最新决定停止形成性评审细则设计，将V-02本轮讨论收口到四场景及共同呈现规则确认，并形成后续Unity任务可直接读取的场景基线。

### 已完成

- 冻结风雨隘口、热浪盐原、雪雾松林、灰霾湿地与四个稳定技术ID的对应关系。
- 汇总2D自动卷轴、东方自然世界、固定观察者、两种互斥呼吸节律提示、低刺激呈现和AI主责资产路线。
- 节点15A转为历史草案，取消节点15B；不再追问人数、问题、问卷或阈值。
- 将实现参数、工程风险排序、动态原型和验证方案移交V-03及后续Unity任务。

### 边界与下一步

- 当前结论是`SCENE_DESIGN_CONFIRMED`，不是任务注册表`DONE`。
- 未产生Unity运行、动态原型、正式构建、真实数据链或正式实验完成证据。
- 下一阶段应从场景基线进入V-03视听映射和实现约束，不再扩展V-02评审设计。

## 2026-08-20 V-02候选验收与职责闭环

### 目标

将V-02场景确认材料转成可审计候选，修正版本化合同、场景设计和Unity实现之间的责任边界，并在真实团队第二人签收前保持V-03阻断。

### 已完成

- 新增机器可读场景基线、技术验收记录、专项校验器和独立Agent复核记录。
- 技术ID按无序集合校验且四模块均`exactly_once`；场景原生与抽象双环共享V-01/R-01四层来源。
- `storm`双停与`fade`双吸均进入v2.2门；新增F-05固定任务负责Schema、fixture和消费者迁移，U-01、U-02、T-01与U-07显式依赖F-05。
- V-03只负责四层视听合同、资产基线和工程风险排序；U-03负责最高风险切片及成本证据；U-08显式依赖G-02资产门。
- 任务注册表扩展为57项，其中54个固定任务和3个模板；依赖图无环且全部任务可到达W-04。
- 独立Agent首轮问题全部关闭，最终结论为`PASS_NO_OPEN_P1_P3`，但不替代真实团队第二人签收。

### 边界与下一步

- V-02候选提交后只迁移到`IN_REVIEW`，V-03继续`WAIT_DEP`；F-05因P-01/P-02尚未签收保持`WAIT_DEP`。
- 本轮没有Unity运行、正式构建、真实设备链、`LIVE_E2E`或参与者结果证据。
- 真实团队第二人必须对固定候选提交给出结论，只有V-02转为`DONE`后才能重新计算并解锁V-03。

## 2026-08-21 V-02真实团队第二人签收与V-03解锁

### 签收

- 傅钧烨以团队总监、真实团队第二人复核身份，对固定候选提交`3ebbdeedfd3c16688ae406d34c18e4f319f2afac`给出`PASS`。
- 日期：`2026-08-21 +08:00`；无未关闭P0-P3问题。
- 第一签收提交：`c04a7be5017164ce8bdfa4ee7f0270c75bb37368`。

### 治理迁移

- V-02从`IN_REVIEW`迁移为`DONE`，签收记录重命名为`V-02_技术验收记录_已签署.md`。
- V-03从`WAIT_DEP`迁移为`READY`；当前可领取集合为F-03、F-04、G-01、V-03。
- 重生成独立任务包后移除V-02复核包，新增V-03包；下游实现仍必须遵守V-03自己的验收门。

### 边界

- V-02签收只关闭四天气场景与呼吸提示设计确认门，不代表Unity运行、正式构建、真实设备链或`LIVE_E2E`完成。
- V-03只负责四层视听映射、资产来源基线和工程风险排序；U-03仍负责最高风险垂直切片实现证据。

### 候选提交与治理迁移

- V-02固定候选提交为`3ebbdeedfd3c16688ae406d34c18e4f319f2afac`。
- 注册表将V-02从`READY`迁移为`IN_REVIEW`；当前可领取集合收敛为F-03、F-04、G-01。
- V-02审核对象固定为上述提交，真实团队第二人结论保持待填写；模型独立复审结论不替代该签收。
- 任务手册、独立任务包和固定任务概要需从迁移后的注册表重新生成并通过一致性验证后，才能形成治理提交。

## 2026-08-23 V-03前期规划与上下游对齐

### 目标与结果

- V-03由Codex领取，分支为`codex/v-03-visual-mapping`，注册状态迁移为`IN_PROGRESS`。
- 新增前期规划、机器可读规划基线和专项校验器，冻结六项执行制品字段、七类风险评分方法与上下游交接门。
- 当前裁定为`READY_FOR_DETAILED_FILL_WITH_F05_PARTIAL_BLOCK`。

### 硬边界

- 本轮未填写四天气详细映射、参数、声音资产、资产条目、风险分数或U-03天气选择。
- F-05签收前，`storm`双停与`fade`双吸的相位级内容保持`BLOCKED_F05`。
- V-03仍非`IN_REVIEW`或`DONE`；本轮没有Unity运行、正式构建、资产许可放行、真实输入链或研究结果证据。

### 下一步队列

1. 依据模板填`heat/snow`共同字段和两条件事件真值。
2. 等待F-05 v2.2签收后填`storm/fade`相位实例。
3. 完成双人风险评分后再选择U-03最高风险天气，不预设旧风暴场景。

### Grill决策01：设计语义与运行字段绑定

- 用户确认V-03可在F-05未完成时完成设计并进入复核。
- V-03使用逻辑相位步骤槽表达`storm`双停与`fade`双吸；F-05后续负责v2.2运行字段绑定。
- F-05只阻断相关下游运行实现，不再作为V-03设计完成的隐含依赖。

### Grill决策02：参与者可见降级类别

- 用户确认后台保留`GOOD/DEGRADED/UNUSABLE/DISCONNECTED`四状态，参与者界面只呈现“低确定性”和“暂不可用”。
- `DEGRADED`继续实际反馈运动但降低轮廓确定性；`UNUSABLE/DISCONNECTED`停止实际相位推进并保留静态断续轮廓。
- 不增加文字、声音、全屏警告或技术原因说明；目标与累计继续服从Python权威。

### Grill决策03：累计状态生命周期

- 用户确认累计状态仅在单个模块内生效：`demo`保持基线，`closed_loop`更新，结束时锁定，`lock_transition`保持后退出。
- 锁定结果不强制达到100%，下一模块从自身中性基线开始，不继承上一模块的视觉累计状态。
- 上一模块最终值只保留在权威记录中，四场景继续保持顺序无关。

### Grill决策04：目标与实际跨层关系

- 用户确认目标与实际允许通过并置运动形成感知同步，但禁止吸附、合并、连线、变色或额外奖励。
- 场景原生条件保持中远景目标与近景实际分离；抽象条件保持外环与内环分层。
- 实际层不得读取目标或误差字段改变自身样式，继续维持跨层独立。

### Grill决策05：相位保持插值

- 用户确认目标和实际只在同一相位内插值，相位真值改变时立即切换运动语义。
- 禁止跨相位平滑、下一相位预测和输入缺帧外推；候选窗口保持`100–250 ms`。
- 精确值由U-03结合外部延迟证据冻结，V-03不提前声明已验证参数。

### Grill决策06：累计环境状态双向映射

- 用户确认累计环境状态双向跟随Python的`recovery_value`，不取历史最大值、不强制单调上升或达到1.0。
- 候选低通为`2–5 s`；四天气分别沿雨势/能见度、热霭/清晰度、雪雾/树线、轮廓/纹理/基础色彩的同一路径双向变化。
- 高值继续保留各天气身份；参与者可见术语统一为“累计环境状态”。

### Grill决策07：共享累计曲线

- 用户确认四天气首版共用线性`0–1`累计曲线，只允许天气定义不同低值和高值端点。
- 禁止场景私有阈值、加速段或更强奖励；同一天气两条件曲线、端点和更新时间完全一致。
- 只有U-03可依据实图可辨识证据提出版本化非线性调整。

### Grill决策08：实际置信包络

- 用户确认`actual_confidence`只控制轮廓连续度、边缘清晰度和有限透明度。
- 相位、进度、速度、尺寸、路径和颜色不受置信度改变；禁止抖动和闪烁。
- 四天气近景实际痕迹与抽象内环共用归一化置信包络，精确视觉范围由U-03证据冻结。

### Grill决策09：U-03风险评分治理

- 用户确认七类风险按`0–4`等权评分，由V-03设计负责人和独立复核者分别给分并保留理由。
- 任一维度差2分以上或最高风险天气不同必须讨论留痕；总分相同按上游合同缺口、条件匹配、降级可读性、性能依次决胜。
- 旧资产存在、制作偏好和视觉吸引力不得影响分数。

### Grill决策10：非节律环境母带候选边界

- 用户确认声音只承担天气空间与连续环境质感，不响应目标、实际、累计环境状态或降级类别。
- 综合响度候选为`-24至-20 LUFS-I`，真实峰值不高于`-3 dBTP`，场景/中性雾廊交叉淡化候选为`2–4 s`。
- 优先完整模块母带；循环时不少于`60 s`且循环点不与呼吸周期对齐。模块从相对时间零确定性起播，不使用运行期随机声音事件。
- 暂停冻结播放位置并停止输出，恢复后续播；同一天气两种提示条件共用相同文件、哈希、起点、循环、响度和包络。精确值由U-03/U-08测量证据冻结。

### Grill决策11：公共横向卷轴与视差候选边界

- 用户在`srp-unity-production-guide`对齐后确认：固定观察者构图不等于相机完全静止，相机只做横向自动前进，高度、旋转、正交尺寸、地平线和提示安全区固定。
- 基础速度候选为`0.015–0.025屏宽/秒`，首选`0.02`；按候选`1920×1080`换算为`28.8–48 px/s`，首选`38.4 px/s`，运行证据同时记录分辨率与像素速度。
- 天空静止或接近静止；最多三个表观卷轴速度带，远景`0.30–0.45`、中景`0.60–0.80`、近景/地面`1.00`。
- 四天气和两提示条件共用相同基础速度，提示层不参与世界视差，速度不受天气身份、目标、实际或累计环境状态改变。
- 暂停冻结全部视觉时间源；U-03用视差预览、接缝录像和暂停逐帧证据冻结精确值，U-08联合验证。像素画候选默认值不适用于当前高分辨率分层插画方向。

### Grill决策12：确定性分段长卷轴资产策略

- 用户确认近景、地面和主要中景使用固定顺序的分段条带，不使用单张巨型运行纹理、短周期可见循环或运行期随机重排。
- 按`1 + 220 s × 0.025屏宽/s`得到`6.5屏宽`最低行程覆盖，加入接缝余量后候选有效覆盖不少于`6.75屏宽`。
- 首版建议四段、每段原始宽度不超过`2屏宽`；相邻重叠`0.10–0.15屏宽`，候选1920宽度下为`192–288 px`。
- 天空静止；远景允许较短的确定性无缝条带，但完整模块内不得出现容易识别的重复地标。
- 所有段共用画布、原点、地平线与提示安全区，拆层后补齐遮挡后方且禁止自动裁边；接缝、透明空洞、补绘断层或明显重复均为退回原因。
- F-03冻结纹理与内存拆分，U-03以静态拼接预览和完整时长滚动录像冻结最终段数。

### Grill决策13：固定构图与提示安全区候选

- 用户确认所有构图采用左下`(0,0)`、右上`(1,1)`的归一化屏幕坐标和`16:9`画面。
- 地平线候选`y=0.56–0.62`，首选`0.59`；同一天气全部分段和两提示条件保持一致。
- 场景原生目标安全区为`x=0.55–0.85, y=0.34–0.72`，实际安全区为`x=0.20–0.45, y=0.18–0.52`；两区不得重叠或被背景持续穿越。
- 抽象双环固定在`(0.50,0.50)`，外环最大直径候选为屏幕短边`18%–24%`；抽象条件关闭场景原生目标与实际层。
- F-03负责世界单位换算，U-03以安全区叠加图、灰阶截图和完整滚动录像冻结精确值；旧像素画相机参数不进入当前方向。

### V-03详细填充里程碑

- 六项候选制品已建立，映射JSON展开`4天气 × 2条件 × 5层 = 40`行，并由生成器与制品校验器检查。
- 参数、声音、资产和公平审查均保留候选/待证据边界，没有扩大为Unity运行、资产许可或正式构建完成。
- 评分者A暂推荐`fade`作为U-03高风险切片；独立评分者尚在只读复核，任务注册表继续保持`IN_PROGRESS`。

### V-03独立复核闭环

- 独立Agent评分为`storm=26、heat=15、snow=25、fade=26`，与评分者A无单维2分差异；按上游合同缺口裁定`fade`。
- 首轮10项P1/P2和后续2项合同问题均已关闭；最终复审`PASS`，无未关闭P0-P2。
- 设计Schema按层冻结源字段与质量行为；默认Python标准库检查通过，冻结`py -3.14`环境的Draft 2020-12验证通过。
- V-03候选可进入现实团队第二人复核，但独立Agent不替代签收，任务注册表在固定候选提交前继续保持`IN_PROGRESS`。
