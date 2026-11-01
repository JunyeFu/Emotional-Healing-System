# 原方案离线数据分析

固定开环A vs 原生受限适应B保持不变。本模块只读原件，不连接TD/Unity，不改变实验时序。`demo / prepare / analyze`构成唯一运行入口；软件演练、真实设备验证和正式研究关闭分别记录。

## 直接运行

```powershell
Set-Location D:\Agent\srp
agent/runtime/srp-analysis.cmd demo --out agent/local/artifacts/my-analysis-demo
agent/runtime/srp-analysis.cmd prepare --bundle D:/SRP-Data/export/bundle.json --out D:/SRP-Data/derived/batch-01
agent/runtime/srp-analysis.cmd analyze --input D:/SRP-Data/derived/batch-01 --out D:/SRP-Data/analysis/batch-01
```

输出目录必须不存在，且不得与输入目录互相包含。`demo`默认30名正式样例、另有5份前置问卷/2名前置人员；这些数字全部合成，不是招募成果。默认包含NA缺题、退出、呼吸未知和P-02断流。`--scenario benefit/null/harm/floor/missing`切换合成情景；`--skip-power`只用于定向处理测试。

功效网格覆盖总N=30/40/48/60、原始分移位-3/0/+3及0/15%后测缺失，使用同一主模型和50次PMM插补。默认每格10次是低预算软件演练，必须同时读Monte Carlo误差；`--power-replications 2000`可重跑较大预算，但合成参数仍不冻结正式N，也不是预期效应。地板情景用`--scenario floor`。

环境在忽略区`agent/local/venvs/analysis/`，不修改BigRun环境。重建当前验证环境：以项目Python3.14创建该venv，再执行该环境的`python -m pip install --only-binary=:all: -r agent/modules/srp_analysis/requirements-lock.txt`。最小运行依赖另见requirements.txt；锁定文件同时包含pytest及PDF检查工具，不修改全局环境。

## 从哪里来，到哪里去

| 原件与责任 | 导入格式 | 派生输出与消费者 |
|---|---|---|
| 设备采集 D-01/D-02，P-02封存 | `device_index.csv`引用P-02归档目录；归档本身不改 | `signals.csv`保留ECG ADC、RR整数、两组XYZ、包/样本索引、时间来源；S-01质量与时钟 |
| P-01/P-02运行事实及实际呈现 | `runtime.csv`规范化只读导出，保留原始L1为证据 | `runtime_facts.csv`；I、有效G、呈现、暂停/帮助/适应/退出 |
| F-02逐题问卷 | `questionnaires.csv` | `questionnaire_items.csv`、参与者NA/PA/努力/舒适，A-02/A-05 |
| X-01原分配 | `allocations.csv` | `participants.csv`；正式随机化、前置人员和前置问卷互不替代 |
| S-02/A-01独立复核标注 | `annotations.csv` | `events.csv`及`participant_modules.csv`；未知不抄G |
| 构建、参数及评分版本 | `analysis_spec.json`和原构建引用 | 计分键、共同I、窗口、可辨性与校准状态；A-03/U12-04 |

六类原件使用既有`RawEvidenceBundle v1`，不另创原件库。一个分析批次的`session_ref`是批次引用；每个实际会话仍保留自己的P-02归档。manifest中规范化表的`artifact_id`固定为`device_index / runtime / questionnaires / allocations / annotations / configuration`；同一family可另列原始L0/L1等文件。实际可运行示例由`demo`生成，格式与P-02原接口一致。

正式存储根沿用`SRP_SESSION_DATA_ROOT`；示例D:/SRP-Data不是已配置声明。联系方式、去重令牌和编号映射不进入分析包。G-02权限、加密、备份恢复及保留期限继续适用。本模块不授予原件访问权，不把受限引用变为可读文件。L0/L1不公开；L2-L4按授权受控；L5汇总另经披露复核，不能将整个分析目录直接上传GitHub。

## 输入字段

- `allocations.csv`：`research_id,cohort,condition,order_id,randomized,completed,withdrawn`。cohort仅survey/pilot/formal；正式随机化者condition=A/B，order_id=1..4。实际完成者不能补填原分配位置。
- `questionnaires.csv`：`research_id,instrument,form_id,timepoint,item_id,value,response_status,measured_at,measurement_delay_s`。PANAS的timepoint=pre/post，NA/PA共20个明确题键。提前离开记录应标departure，不能冒充主要post；原始时点及延迟始终保留。effort/comfort为各0..10自编单题。
- 问卷response_status为RESPONDED/SKIPPED/TIMEOUT/NOT_PRESENTED；非回应不计为0，缺一题只令其所属分量表缺失。缺测与真实最低分10不同。两组前后测须同一最终题本与此刻指令；工作译稿不是正式核准题本。
- `runtime.csv`：`research_id,module_id,kind,start_s,end_s,cycle_id,step_id,phase,I_duration_s,presented`。kind=module/G/adaptation/pause/help/exit；module提供固定起止T，G只导入实际有效提示，presented仅有呈现证据才true。start/end是已经S-01对齐的共同实验秒，不自行推断时钟映射。
- `annotations.csv`：`research_id,module_id,cycle_id,step_id,phase,start_s,end_s,status,source,validation_ref`。source只认independent_annotation/validated_detector，必须有独立验证引用；status=UNKNOWN或不完整周期保留未知。编号来自离线标注，不抄在线成功/周期标签。
- `device_index.csv`：`research_id,archive_ref,host_origin_ns`。archive_ref在bundle根内指向归档目录。解码使用P-02严格封存核验；主机接收时间、名义批次时间不冒充已校准设备时钟。
- 配置模板见[analysis-spec.template.json](analysis-spec.template.json)。未核实字段为null/false，不用演练数值替代；真实时钟映射/事件验证、单位、采样率与门槛由S-01/S-02/Q-03提供。模板的量表题键仅是一般NA10/PA10工作映射，最终表单必须重新核对。

当前运行适配的是上述明确的规范化CSV导出与BigRun P-02包；不会自动识别任意问卷平台列名，也没有实现新的在线呼吸检测器。导出者按字段契约提供实际事实。不能识别的呼吸步骤仍未知，PANAS路径不因此删除。

## 计算定义

I达成：独立实际X的完整周期满足天气步骤次序和相位，逐步骤时长对比共同I，不作时间伸缩。G跟随：独立X步骤对比最近的同名实际有效G步骤，起止边界及相位均满足同一容差才计跟随。跨模块仅保留实际预算内时长，不重复归属。

每模块固定T分为C（符合）、K（已观察但不符合）与U（未知），C+K+U=T；分别输出C/T、(C+U)/T、C/(C+K)和覆盖。I与G分别计算可比较范围：有X但没有对应G呈现证据，G仍属未知，不计失败。无容差只给连续误差和覆盖，不给合格分类。无观察时下界0、上界1是未知界，不是将缺失填为真实零分。参与者汇总只有四模块均可计算才等权平均，不重分配缺模块权重。技术不可观测不作执行失败。

HRV仅在单位、逐搏连续性和质量均有验证引用时，对预设等长连续窗口计算RMSSD/SDNN；异常RR和显式断流切断窗口，不补搏，不跨段拼接。窗口按连续RR相对时间固定分段，RR按末搏落窗，不在边界插值或把每窗延长到下一搏；输出窗起止、等长覆盖时长、RR数量及RR和分时长。RR相对时间不是已校准设备或实验时钟。未核准的原生RR仍只保留整数。呼吸代理不作为真实X、不凭低幅识别停留/补吸；HRV不作为情绪收益的代证。

主模型：`NA_post ~ B + centered_NA_pre + order_2 + order_3 + order_4`，B-A，HC3、双侧95%区间，参与者是单位。缺失使用statsmodels MICE-PMM k=5、50条独立种子链、每链20轮；同模型HC3后Rubin方差合并，Barnard-Rubin小样本自由度。PMM只取观察供体，所以NA保留10..50；不以前测代填后测。基线缺失联合插补；整臂没有观察值、结局无变化或模型不可估计时明确报告，不用数值噪声制造精度，不删顺序/换终点。score_distribution.csv单列观察分布与地板/天花板。

完全案例与按A/B分别delta偏移缺失后测同时报告；delta仅作用于缺失后测并限制10..50。默认delta组合只是软件情景，正式域仍须冻结。可选插补预测变量必须是事前记录的数值列，不自动将处理后变量纳入。PA、努力、舒适与功能指标提供描述统计，不假装增加确认性终点；理解回应保留逐题计数，没有验证题键不生成总分。

## 结果包与解读

`estimates.csv / analysis.json`为主要估计，`missingness_sensitivity.csv`为缺失敏感性；`secondary_results.csv`、`hrv_windows.csv`、`participant_modules.csv`为次要/探索。`imputations/`保存每次完成数据供受控复算，不冒充观察值。`qc.csv`保留分域缺失，`cohort_counts.csv`分开样本；`data_dictionary.json`提供实际文件字段和单位。

图01样本流；图02观察个体前后NA；图03B-A及敏感性区间；图04参与者努力/舒适/适应次数分布；图05覆盖；图06固定选中位和低覆盖过程案例。`participant_costs.csv`另给四模块时间、帮助、暂停和退出总量；记录不完整时总成本留空。每图有PNG/PDF，且标证据类别。`report.md / report.pdf`给出数据、方法、结果、解释和待关闭研究条件。`power_grid.csv/json`及`power_precision.png/pdf`是样本精度情景。每格全拒绝或全不拒绝时插件Monte Carlo标准误为0，不代表真实概率已知；正式规划需足够模拟预算及前置数据。

CI全负支持本次完整B方案NA较低，全正支持A较低；CI跨零是方向不确定，不是等效/无效。实际意义还需事前关注差。没有休息对照不推断绝对收益；没有机制操纵不拆出自适应、天气或视觉单机制因果效应。I达成、G跟随、负担及成本分开，情绪结果不被旧PF门隐藏。

本入口始终标记`formal_analysis_authorized=false`：它不是新的研究准入/锁库授权入口。真实数据可作有权限的初步分析，但正式A-05仍须E-04锁库、揭盲授权、正式SAP和独立复算。软件完成不改变这些业务状态。

## 验证

```powershell
agent/local/venvs/analysis/Scripts/python.exe -m pytest agent/modules/srp_analysis/tests -q
```

新增和历史范围分开核查；旧前测代填功效器移入历史归档，当前入口不再调用。原历史签收、任务状态及领取快照保留。

方法实现依据：[statsmodels MICEData](https://www.statsmodels.org/stable/generated/statsmodels.imputation.mice.MICEData.html)、[MICE update_all](https://www.statsmodels.org/stable/generated/statsmodels.imputation.mice.MICEData.update_all.html)、[OLS HC3](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html)、[mice的Barnard-Rubin实现](https://github.com/amices/mice/blob/master/R/barnard.rubin.R)。本地活动统计规格见U12-04，研究主张边界以当前07协议为准。
