"""Fixed figures and source-linked reports; not automated scientific acceptance."""
from html import escape

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak

from .io import save_frame

COLORS = {'A': '#187f7e', 'B': '#cf573c'}
RULES = {
    'B_LOWER_NA_WHOLE_PACKAGE_ONLY': '本样例B的基线校正NA较低；仅限所比较的完整方案，不证明单独自适应机制或长期收益。',
    'A_LOWER_NA_WHOLE_PACKAGE_ONLY': '本样例A的基线校正NA较低；应如实报告，不能因B未获优势而改换终点。',
    'DIRECTION_UNCERTAIN_NOT_EQUIVALENCE': '方向证据不足，报告估计与区间；不能解释为等效或没有效果。',
}


def _save(fig, out, title, evidence):
    fig.suptitle(f'{evidence} | {title}', fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(out / f'{title}.png', dpi=160)
    fig.savefig(out / f'{title}.pdf', metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


def figures(data, modules, events, runtime, primary, sensitivity, out, evidence, costs):
    out.mkdir()
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(8.4, 3.5))
    x = np.arange(4)
    for j, condition in enumerate(('A', 'B')):
        group = data.loc[data.condition.eq(condition)]
        counts = [len(group), int(group.completed.sum()), int(group.NA_post.notna().sum()), int(group.withdrawn.sum())]
        ax.bar(x + (j - .5) * .32, counts, width=.32, color=COLORS[condition], label=condition)
    ax.set_xticks(x, ['Randomized', 'Completed', 'NA post observed', 'Withdrawn'])
    ax.set_ylabel('Independent participants')
    ax.legend()
    _save(fig, out, '01_participant_flow', evidence)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7), sharey=True)
    for ax, condition in zip(axes, ('A', 'B')):
        group = data.loc[data.condition.eq(condition)]
        for i, row in enumerate(group.itertuples()):
            shift = ((i % 7) - 3) * .014
            ax.plot([shift, 1 + shift], [row.NA_pre, row.NA_post], color=COLORS[condition], alpha=.45, marker='o', ms=3)
        ax.set(title=f'{condition}: raw observed NA; n={len(group)}', xticks=[0, 1], xticklabels=['Pre', 'Post'], ylim=(9, 51))
    axes[0].set_ylabel('NA sum (10-50); missing not imputed in plot')
    _save(fig, out, '02_individual_NA', evidence)
    fig, ax = plt.subplots(figsize=(8.4, 3.7))
    rows = [dict(primary, analysis_set='PRIMARY'), *sensitivity]
    rows = [r for r in rows if r.get('status') == 'ESTIMATED']
    for i, row in enumerate(rows):
        ax.errorbar(row['beta'], i, xerr=[[row['beta'] - row['ci_lower']], [row['ci_upper'] - row['beta']]],
                    fmt='o', capsize=3, color='#187f7e' if i == 0 else '#707070')
    labels = [r['analysis_set'] + (f" A:{r.get('delta_A', 0):+g} B:{r.get('delta_B', 0):+g}"
                                 if 'delta_A' in r else '') for r in rows]
    ax.set_yticks(range(len(rows)), labels)
    ax.axvline(0, color='#777777', linestyle='--', lw=1)
    ax.set_xlabel('Adjusted NA difference B - A (95% CI); negative favors B')
    if not rows:
        ax.text(.5, .5, primary.get('reason', 'NOT ESTIMABLE'), transform=ax.transAxes, ha='center')
    _save(fig, out, '03_adjusted_difference', evidence)
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 3.5))
    for ax, metric in zip(axes[:2], ('effort', 'comfort')):
        for j, condition in enumerate(('A', 'B')):
            values = data.loc[data.condition.eq(condition), metric].dropna()
            if len(values):
                ax.scatter(np.full(len(values), j) + np.linspace(-.06, .06, len(values)), values,
                           color=COLORS[condition], alpha=.6, s=13)
                ax.plot([j - .12, j + .12], [values.median()] * 2, color='black', lw=2)
        ax.set(title=metric, xticks=[0, 1], xticklabels=['A', 'B'], ylim=(-.5, 10.5))
    for j, condition in enumerate(('A', 'B')):
        values = costs.loc[costs.condition.eq(condition), 'adaptation_count'].dropna()
        axes[2].scatter(np.full(len(values), j) + np.linspace(-.06, .06, len(values)), values,
                        color=COLORS[condition], alpha=.6, s=13)
        if len(values):
            axes[2].plot([j - .12, j + .12], [values.median()] * 2, color='black', lw=2)
    axes[2].set(title='Adaptations per participant', xticks=[0, 1], xticklabels=['A', 'B'],
                ylabel='Cost, not benefit; missing excluded')
    _save(fig, out, '04_effort_comfort_cost', evidence)
    fig, ax = plt.subplots(figsize=(8.4, 3.5))
    weather_order = ['storm', 'heat', 'fade', 'snow']
    for j, condition in enumerate(('A', 'B')):
        group = modules.loc[modules.research_id.isin(data.loc[data.condition.eq(condition), 'research_id'])]
        means = group.groupby('module_id').observed_coverage.mean().reindex(weather_order) if 'observed_coverage' in group else pd.Series(np.nan, index=weather_order)
        ax.bar(np.arange(4) + (j - .5) * .32, means, width=.32, color=COLORS[condition], label=condition)
    ax.set(xticks=np.arange(4), xticklabels=weather_order, ylim=(0, 1), ylabel='Observable X / fixed exposure budget')
    ax.legend()
    _save(fig, out, '05_signal_coverage', evidence)
    cases = []
    if 'observed_coverage' in modules:
        quality = modules.loc[modules.research_id.isin(data.research_id)].groupby('research_id').observed_coverage.mean().dropna().sort_values(kind='stable')
        if len(quality):
            cases = [{'research_id': quality.index[0], 'selection': 'lowest_observed_coverage'},
                     {'research_id': quality.index[len(quality) // 2], 'selection': 'median_observed_coverage'}]
    save_frame(out.parent / 'process_cases.csv', pd.DataFrame(cases, columns=['research_id', 'selection']))
    fig, axes = plt.subplots(max(1, len(cases)), 1, figsize=(8.4, 2.2 * max(1, len(cases))))
    if not cases:
        np.atleast_1d(axes)[0].text(.5, .5, 'No observable process records', ha='center', transform=np.atleast_1d(axes)[0].transAxes)
    for ax, case in zip(np.atleast_1d(axes), cases):
        rid = case['research_id']
        group = runtime.loc[runtime.research_id.eq(rid) & runtime.module_id.eq('fade') & runtime.kind.eq('G')]
        for r in group.itertuples():
            ax.broken_barh([(r.start_s, r.end_s - r.start_s)], (1, .25), facecolors='#187f7e')
        group = events.loc[events.research_id.eq(rid) & events.module_id.eq('fade')]
        for r in group.itertuples():
            ax.broken_barh([(r.start_s, r.end_s - r.start_s)], (.4, .25), facecolors='#cf573c' if r.observed else '#bbbbbb')
        ax.set(title=f"{rid}: {case['selection']} (illustration, not effect evidence)", yticks=[.52, 1.12], yticklabels=['X', 'G'], xlabel='Common experiment time (s)')
    _save(fig, out, '06_prespecified_process_cases', evidence)


def write_report(out, data, modules, qc, result, summary):
    evidence = result['evidence_class']
    spec = result['spec']
    primary = result['primary']
    conclusion = RULES.get(primary.get('interpretation'), '主要模型不可估计；保留原因，不自动更换模型或终点。')
    if evidence != 'SYNTHETIC':
        conclusion = conclusion.replace('本样例', '本次数据中的')
    lines = ['# SRP 数据分析报告', '', f'证据类别：{evidence}。软件分析不等于研究批准或真人验收。', '',
             '## 数据与方法', '固定开环A与原生受限适应B保持原设定。仅随机化正式参与者进入主要模型。',
             f"本次主要分析分配人数：{len(data)}；前置问卷与预试人数另见 cohort_counts.csv。",
             '模型：NA_post ~ B + centered_NA_pre + 四天气顺序固定效应；HC3、双侧95%区间。',
             'NA/PA各10题，1至5求和10至50，缺题则该分量表缺失；不合成20题总分。',
             '观察分数的地板/天花板人数、比例、缺失及范围见 score_distribution.csv；插补值不冒充观察分布。',
             f"缺失时使用PMM k={spec['pmm_k']}、{spec['imputations']}插补、每链{spec['iterations']}轮；HC3后Rubin合并，使用Barnard-Rubin小样本自由度。",
             '原始X未知不用G补造；参与者功能汇总固定四模块等权，不按可用模块重新加权。', '',
             '## 主要结果', f"状态：{primary['status']}"]
    if primary['status'] == 'ESTIMATED':
        lines += [f"B - A = {primary['beta']:.3f}分；95%CI [{primary['ci_lower']:.3f}, {primary['ci_upper']:.3f}]；双侧p={primary['p_value']:.4g}。"]
    else:
        lines += [f"原因：{primary.get('reason')}。"]
    lines += [conclusion, '区间跨零不是等效；没有休息对照不证明绝对收益；没有独立机制操纵不归因于单一机制。', '',
              '## 功能、成本与探索', 'I达成、G跟随、覆盖、未知、适应、暂停、帮助和退出分开见 participant_modules.csv。',
              '参与者成本分布见 participant_costs.csv；四模块记录不完整时总成本留空，不将缺记录填0。',
              'PA、努力与舒适见 secondary_results.csv，理解题回应见 questionnaire_process.csv；没有冻结题键不制造理解总分。',
              'HRV见 hrv_windows.csv；不跨断流拼接，不把HRV变化直接解释为情绪收益。', '',
              '## 缺失与敏感性', '主要后测缺失与信号缺失分别记录；有效PANAS不因设备失败删除。',
              'missingness_sensitivity.csv 包含完全案例及分组delta偏移；delta只作用于缺失后测，限制在10至50。',
              '当前delta域是软件演练候选，不是已批准的正式MNAR域。没有缺失时无需伪造插补。', '',
              '## 图表与复算', '图01样本流；图02原始个体NA前后变化；图03调整后差异；图04努力/舒适/成本；图05覆盖；图06预先规定的中位/低覆盖过程案例。',
              '原始观察图不显示插补成真实观察。个例只能说明过程，不能代替组间估计。',
              '输入身份、代码摘要、依赖版本和模型设定见 analysis.json；字段与单位见 data_dictionary.json；结果到输入列的关系见 result_sources.csv。', '',
              '## 尚未关闭的研究条件', '真实设备单位/时钟与质量、真实呼吸事件验证、中文量表定稿、正式SAP、锁库和揭盲授权尚未由本软件关闭。',
              '所有合成图表明确标识SYNTHETIC，不是研究结果。']
    (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    body = ParagraphStyle('Chinese', fontName='STSong-Light', fontSize=9.5, leading=14, spaceAfter=5, wordWrap='CJK')
    heading = ParagraphStyle('ChineseHeading', parent=body, fontSize=13, leading=18, spaceBefore=8)
    story = []
    for line in lines:
        if not line:
            story.append(Spacer(1, 5))
        else:
            story.append(Paragraph(escape(line.lstrip('# ')), heading if line.startswith('#') else body))
    for i, path in enumerate(sorted((out / 'figures').glob('*.png'))):
        if i % 2 == 0:
            story.append(PageBreak())
        story.append(Image(str(path), width=475, height=210 if i != 5 else 230, kind='proportional'))
        story.append(Spacer(1, 12))
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#555555'))
        canvas.drawString(42, 25, f'{evidence} | CANDIDATE ANALYSIS - NOT RESEARCH ACCEPTANCE')
        canvas.drawRightString(550, 25, str(doc.page))
    SimpleDocTemplate(str(out / 'report.pdf'), pagesize=(595, 842), rightMargin=48, leftMargin=48,
                      topMargin=38, bottomMargin=42, invariant=1, title='SRP Analysis Report').build(story, onFirstPage=footer, onLaterPages=footer)
