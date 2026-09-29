# U12-11 十五项冻结交付映射

字段名称逐项沿用研究protocol_authority_v1.2.required_freezes。状态与证据入口只读[G-03空索引](../../G-03/outputs/freeze-template.json)，目前15项全部PENDING、evidence_ref为空。本表说明应交什么，不是另一个批准登记表。

| 权威字段 | 应交材料和裁定 | 提供任务与实际缺口 |
|---|---|---|
| panas_version_and_permission | 许可版本、题项映射、此刻框架、计分与缺题规则 | F-02/A-03/G-05；真实许可与校准未齐 |
| eligibility_and_recruitment | 获批人群、纳排、招募渠道、一次参与和退出规则 | G-05/G-03；机构人群与真实材料待批 |
| training_budget | 两条件相同有限预算、教学呈现构建和计时规则 | U12-03；180秒仅候选，正式预算为空 |
| randomization_and_concealment | 隐藏清单、分层/区组、角色揭示和版本 | X-01/G-03；原清单工具签收不等于本研究正式清单 |
| minimum_important_affect_difference | PANAS量尺上的事前关注差异、独立理由和批准 | U12-11/A-03-CAL；正式差异为空，不由现有N倒推 |
| missingness_and_mnar | 分析集、量表/信号分别处理、有界MI/Rubin/MNAR及敏感性网格 | A-02/A-03/U12-04；正式流水线及网格未交付 |
| functional_margin_justification | 两分析集机会PF、0.075候选界值的理由及实际采用决定 | A-03-CAL/A-02/U12-11；候选不能直接批准 |
| critical_error_thresholds | 步骤/模块严重错误定义、盲态证据和阈值 | U12-02/Q-03/A-03-CAL；真实阈值为空 |
| final_power_and_n | 真实盲态参数、PANAS与护栏联合可行性、类型I/Monte Carlo误差、最终N和上限 | A-03-CAL/U12-11；正式N/上限为空，合成主效应网格不足 |
| stopping_rule | 按随机分配N停止，或事前批准盲态重估及上限/触发规则 | U12-11/G-03；不得按p值、方向或完成者补格 |
| institutional_scope | 覆盖阶段一、量表和现场活动的真实批准、责任人及版本 | G-05；对应真实回执为空 |
| live_e2e | 真设备、Unity独立于TD、800秒完整链、回执/记录/故障证据 | I-01/D-01/D-02/U-08；真实链尚未交付 |
| runtime_gate_integration | 六正式入口消费冻结/资格、版本匹配和负测 | U12-06/U12-09；在研接线与正式一致性仍缺 |
| data_retention_and_access | 获批最短必要期限、权限角色、专机/受限原件访问及撤回处理 | G-02/G-05；治理工具DONE不等于机构批准期限 |
| pretreatment_baseline_and_condition_training_order | 中性准备→PANAS前测→揭示→条件教学→核心→后测；处理含教学、首次教学暴露登记 | U12-03/X-01/P-01/U12-06；时序待冻结，当前核心start登记不能覆盖教学 |

“提供任务”是职责路由，不是实名领取或真实签名。统计、研究、工程、数据、现场和独立复核人应在实际任务领取与冻结材料中落实，不填写Agent虚构的负责人。

确认性等效默认关闭，它不是第16个必需启用项。关闭时不要求填写等效界/方法来装作获批；若确需启用，应在正式结果访问前另行受控冻结界值、方法、alpha、区间对应、缺失、多重声明和功效，不由本包默认添加。
