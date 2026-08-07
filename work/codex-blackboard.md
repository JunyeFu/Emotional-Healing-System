# Codex Blackboard

> Purpose: lightweight project-local working memory for the current task. Keep this file factual, brief, and easy to reset.

## Current Task Goal

输出一份可导航的项目情况与顶层设计汇总，区分仓库现状、已确认目标、建议研究方案、尚待确认门和进入成员任务包拆分前的顺序。

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

## Known Evidence

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
