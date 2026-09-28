"""Build F-02's current usage entry from the adopted research authorities."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
OUTPUT = ROOT / 'agent/tasks/F-02/outputs/current-measurement.md'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def build_text():
    authority = load(PLAN / '00_总控/protocol_authority_v1.2.json')
    sap = load(PLAN / '24_团队任务与项目治理/u12_upgrade/U12-04_panas_sap/contract.json')
    for section, fields in {
        'primary': ('outcome', 'candidate_model', 'report_even_if_functional_guard_fails'),
        'manipulation_check': ('role', 'blocks_prespecified_outcome_reporting'),
        'missingness': ('sensor_failure_does_not_drop_valid_panas',),
    }.items():
        for field in fields:
            if sap[section][field] != authority[section][field]:
                raise ValueError(f'F-02 authority/SAP disagreement: {section}.{field}')
    primary = authority['primary']
    manipulation = authority['manipulation_check']
    if not primary['report_even_if_functional_guard_fails']:
        raise ValueError('Current primary reporting rule requires controlled reassessment')
    if manipulation['role'] != 'manipulation_only' or manipulation['blocks_prespecified_outcome_reporting']:
        raise ValueError('Current SCCI role requires controlled reassessment')
    prefix = '../../../../' + PLAN.relative_to(ROOT).as_posix()
    return f"""# F-02 当前构念与测量适用说明

本入口供当前任务执行使用；历史v0.9候选、原验收与冻结快照保留不改。当前研究主线比较两种完整提示方案，不保证原生提示胜出。

## 当前结果角色

- 主要结果：`{primary['outcome']}`。
- 候选模型：`{primary['candidate_model']}`，预设情绪比较不因功能门失败而隐去。
- SCCI：`{manipulation['role']}`，只检验表示差异是否被感知；不单独证明理解、执行或情绪收益。
- 呼吸执行质量、理解、心智努力用于功能与解释边界，不沿用旧有序联合门作为情绪结果报告门。
- 传感器失败不自动剔除有效PANAS。缺失分析和最终研究数值由U12-04及研究冻结流程负责。
- 确认性等效检验默认不开启，未显著不代表等效。

## 候选条目怎样使用

| 历史内容 | 当前处置 | 权威或执行位置 |
|---|---|---|
| S1至S4与储备条目 | 保留操纵检查候选，Level A/B后选定；不按情绪效果挑题 | 历史F-02第4节，Q-01/Q-02 |
| C-T1、C-T2 | 改为当前及下一目标具体步骤，保留周期边界 | U12-02 |
| C-A1、C-A2 | 改为可读取实际步骤及同周期同一步等身份关系；未知为null | U12-02 |
| C-C1、C-C2 | 改为真实片段累计区间及起终点变化，不使用常识固定答案 | U12-02 |
| C-D1、C-D2 | 当前输入可用性与可读取的信息 | U12-02 |
| 心智努力及目的猜测 | 保留候选，仍需认知访谈与分析冻结 | 历史F-02第6、14节 |
| 专家审查与两条件访谈 | 保留构念纯度、覆盖、用时和差异审查方法 | Q-01/Q-02当前材料 |
| 旧Gate2联合门与“只能报告”规则 | 对新研究不再适用；历史原件仅作来源 | v1.2与U12-04 |

题面在两条件保持中性且同源。理解题安排在PANAS后测之后，800秒体验期间不增加参与者操作。非作答保留RESPONDED、SKIPPED、TIMEOUT、TECH_UNPRESENTED状态，不补零、不替下游决定分母。步骤身份一致不等于执行合格。

## 流程与用时

当前候选顺序：中性介绍 → PANAS前测 → 等预算分条件教学 → 800秒体验 → PANAS后测 → 理解、操纵与负担候选测量。教学预算和正式时序仍须受控冻结，不能把此说明当成已完成准入。

旧230秒是候选预算，不是实测。本包问卷目标仍不超过5分钟；由Q-02记录两条件实际用时和逐题问题，超预算时修订再测。PANAS及整个活动总时长另由研究流程核算。

## 责任与待完成事项

本轮Codex完成适用入口、结构整理和代码复测。历史F-02审查人为Codex，不能写成傅钧烨签收。本轮不改变F-02注册状态，也不补签其历史原件。

Q-01/Q-02负责真实内容审查与认知过程证据；S-02负责独立真实标注；U-02/U-07负责同源渲染片段；U12-04负责计分与缺失分析；研究负责人完成版本、许可、教学、数值和机构准入冻结。这里只列任务职责，人员实际领取仍读注册表。

候选代码和合成材料验证不证明实际信号可识别或心理测量有效。正式采集当前仍未准入。

## 可打开的来源

- [历史候选材料]({prefix}/03_步骤02_构念比较条件与测量/01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md)
- [历史模型审查]({prefix}/03_步骤02_构念比较条件与测量/02_F-02_验收记录.md)
- [当前研究合同]({prefix}/00_总控/protocol_authority_v1.2.json)
- [当前步骤测量](../../../../02-技术研发/srp_step_measurement/README.md)
- [当前分析规格]({prefix}/24_团队任务与项目治理/u12_upgrade/U12-04_panas_sap/contract.json)

复测入口：`agent/tasks/F-02/execution/verify.ps1`。人类总结从同包结构化summary生成，不直接修改Word掩盖执行层差异。
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = build_text()
    if args.check:
        if OUTPUT.read_text(encoding='utf-8') != text:
            raise ValueError('F-02 current usage entry is outdated; regenerate it')
        print('PASS: F-02 usage matches adopted authority and SAP')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(text, encoding='utf-8')
        print(OUTPUT)


if __name__ == '__main__':
    main()
