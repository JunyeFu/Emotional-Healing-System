"""Generate current human LaTeX/PDF reviews from task execution summaries."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from review_latex import Review, compile_pdf, escape, verify_review

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / 'agent/governance/planning/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def document(title):
    return Review(title)

def render_summary(summary, output):
    doc = document(summary['title'])
    compact_sources = bool(summary.get('operational_design_candidate'))
    doc.add_paragraph(f"审阅日期 {summary['review_date']}    任务 {summary['task_id']}")
    groups = {0: (1, '一、任务定义与交付'), 3: (2, '二、执行与验证'),
              7: (3, '三、审阅与交接')}
    for index, section in enumerate(summary['sections']):
        if index == 10 and compact_sources:
            doc.parts.append(r'\begin{minipage}{\linewidth}')
        if index in groups:
            group_number, group_title = groups[index]
            group_start = index
            doc.add_heading(group_title, level=1)
        doc.add_heading(f"{group_number}.{index - group_start + 1} {section['heading']}", level=2)
        if index == 0:
            doc.add_paragraph(summary['conclusion'])
        for paragraph in section['paragraphs']:
            doc.add_paragraph(paragraph)
        for figure in summary.get('figures', []):
            if figure['after_section'] == section['heading']:
                doc.add_picture(ROOT / figure['path'], figure['caption'])
        if index == 8:
            acceptance = summary['historical_acceptance']
            doc.add_paragraph(f"历史审核人 {acceptance['reviewer']}    日期 {acceptance['date']}")
            if acceptance.get('commit'):
                doc.add_paragraph(f"历史审核提交 {acceptance['commit']}")
            doc.add_paragraph(acceptance['method'])
    if compact_sources:
        # The operation design adds seven links; keep their heading and sources together.
        doc.parts.append(r'\begingroup\small\setlength{\tabcolsep}{4pt}\begin{tabular}{@{}p{0.48\linewidth}p{0.48\linewidth}@{}}')
        links = []
        for source in summary.get('source_links', []):
            uri = (ROOT / source['path']).resolve().as_uri().replace('%', r'\%')
            links.append(r'\href{' + uri + '}{' + escape(source['label']) + '}')
        for start in range(0, len(links), 2):
            cells = links[start:start+2]
            if len(cells) == 1:
                cells.append('')
            doc.parts.append(' & '.join(cells) + r'\\[4pt]')
        doc.parts.append(r'\end{tabular}\endgroup\end{minipage}\par')
    else:
        for source in summary.get('source_links', []):
            doc.add_link(ROOT / source['path'], source['label'])
    doc.save(output)
    return output

def check_task(task_id, registry):
    if task_id not in registry:
        raise ValueError(f'Unknown task: {task_id}')
    package = ROOT / 'agent/tasks' / task_id
    required = ('TASK.md', 'inputs/sources.json', 'execution/verify.ps1',
                'evidence/verification.json', 'outputs/summary.json', 'archive/README.md')
    for path in required:
        if not (package / path).is_file():
            raise ValueError(f'Missing package file: {task_id}/{path}')
    allowed_dirs = {'inputs', 'execution', 'evidence', 'outputs', 'archive'}
    if task_id == 'T-01':
        allowed_dirs.add('design')  # Existing device-preview design assets belong to this task.
    for entry in package.iterdir():
        if entry.name != 'TASK.md' and entry.name not in allowed_dirs:
            raise ValueError(f'Unclassified package file: {entry}')
    for source in read_json(package / 'inputs/sources.json')['paths']:
        resolved = (ROOT / source).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            raise ValueError(f'Missing source: {source}')
    summary = read_json(package / 'outputs/summary.json')
    evidence = read_json(package / 'evidence/verification.json')
    if summary['task_id'] != task_id or evidence['task_id'] != task_id:
        raise ValueError('Task identity mismatch')
    headings = ('当前结论', '目标与完成标准', '实际交付', '执行过程与关键决定',
                '验证与结果', '偏离与修复闭环', '目录与文件整理', '上下游交接',
                '审阅与责任签收', '收尾与下一包', '审阅来源')
    if tuple(section['heading'] for section in summary['sections']) != headings:
        raise ValueError(f'Summary does not follow the common template: {task_id}')
    if not evidence['checks']:
        raise ValueError(f'Missing verification record: {task_id}')
    for check in evidence['checks']:
        if check['exit_code'] != 0 and not check.get('disposition'):
            raise ValueError(f'Undocumented verification failure: {task_id}')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_id')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--chain-only', action='store_true', help='Update chained review without rewriting the task LaTeX/PDF')
    args = parser.parse_args()
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    registry = {r['task_id']: r for r in rows}
    task_ids = list(registry) if args.task_id == 'ALL' else [args.task_id]
    if args.check:
        for task_id in task_ids:
            summary = check_task(task_id, registry)
            verify_review(ROOT / 'human/tasks' / task_id / 'summary.tex', summary)
        print(f'PASS package structure, LaTeX/PDF and sources: {len(task_ids)} packages')
        return
    if not args.chain_only:
        for task_id in task_ids:
            summary = check_task(task_id, registry)
            target = render_summary(summary, ROOT / 'human/tasks' / task_id / 'summary.tex')
            compile_pdf(target)
    chain = document('SRP 任务包串联审阅')
    chain.add_paragraph('本文件由71包Agent层总结串联生成，检查实际交付、上下游衔接及项目偏离。规范化与任务业务状态分开；未完成的运行、研究和审批仍由原任务承担。')
    chain.add_paragraph('2026年10月8日71包同步固定开环A与原生受限适应B任务基线；共享I、下发G、独立X及同预算。历史状态与签收保留原范围，全部新范围验收另取证；8个策略扩展不成为核心依赖。Storm及粒子帧仅为历史资产参考。')
    chain.add_picture(ROOT / 'human/assets/previews/2026-10-08/member-storm-particle-rings/video-02-t26.png', '成员视频2第26秒原帧，底部脚本缺失警告保留；工程测试与实际验收仍按对应任务实施。')
    completed = []
    findings = []
    for row in rows:
        path = ROOT / 'agent/tasks' / row['task_id'] / 'outputs/summary.json'
        if not path.exists():
            continue
        item = read_json(path)
        completed.append(row['task_id'])
        chain.add_heading(f"{row['task_id']} {row['domain']}", level=1)
        chain.add_paragraph(item['conclusion'])
        handoff = next(s for s in item['sections'] if s['heading'] == '上下游交接')
        for paragraph in handoff['paragraphs']:
            chain.add_paragraph(paragraph)
        for finding in item['findings']:
            findings.append({'task_id': row['task_id'], **finding})
            chain.add_paragraph(f"{finding['id']} {finding['status']}：{finding['description']}")
    layout = read_json(ROOT / 'agent/root-layout.json')
    chain.add_heading('逐包整理结果', level=1)
    remaining = [r['task_id'] for r in rows if r['task_id'] not in completed]
    complete = layout['root_migration_complete']
    next_task = remaining[0] if remaining else ('业务任务按注册表推进' if complete else '当前总结刷新与整体完成审计')
    completion = '已完成并验证' if complete else '尚待整体完成审计'
    count = chain.add_paragraph(f"已整理{len(completed)}包，待整理{len(remaining)}包；根目录双层整理{completion}。下一项{next_task}。")
    if remaining:
        queue = chain.add_paragraph('、'.join(remaining))
    migrated = [e for e in layout['entries'] if e['status'] == 'MIGRATED']
    pending = [e for e in layout['entries'] if e['status'] != 'MIGRATED']
    migration_heading = chain.add_heading('根目录物理迁移', level=1)
    chain.add_paragraph(f"实际迁移{len(migrated)}/{len(layout['entries'])}项，尚余{len(pending)}项；整体双层整理{completion}。逐包整理不代替运行入口、生成器、历史原件及当前LaTeX/PDF来源检查。")
    for entry in migrated:
        chain.add_paragraph(f"{entry['old']} → {entry['new']}")
    chain.add_paragraph('旧框架及Mock/Spout手册已原样归档，当前人类概览位于human/project/README.md，运行入口位于agent/runtime/README.md。业务签署和进行中分发不因迁移而改变。')
    chain.add_heading('迁移批次历史记录', level=2)
    chain.add_paragraph('以下为各批完成时的原始记录，其中下一步和未完成表述保留当时语境；当前结果以上方逐包整理结果及根目录归属表为准。')
    if any(e['old'] == 'output' for e in migrated):
        delivery = read_json(ROOT / 'agent/evidence/root-migration-deliverables.json')
        chain.add_paragraph(delivery['human_review'])
    if any(e['old'] == '04-成果与交付' for e in migrated):
        delivery_source = read_json(ROOT / 'agent/evidence/root-migration-delivery-source.json')
        chain.add_paragraph(delivery_source['human_review'])
    if any(e['old'] == '00-项目管理' for e in migrated):
        governance = read_json(ROOT / 'agent/evidence/root-migration-governance.json')
        chain.add_paragraph(governance['human_review'])
    if any(e['old'] == '01-需求与设计' for e in migrated):
        support = read_json(ROOT / 'agent/evidence/root-migration-support.json')
        chain.add_paragraph(support['human_review'])
    if any(e['old'] == '02-技术研发' for e in migrated):
        modules = read_json(ROOT / 'agent/evidence/root-migration-modules.json')
        chain.add_paragraph(modules['human_review'])
    if any(e['old'] == '.artifacts-local' for e in migrated):
        local = read_json(ROOT / 'agent/evidence/root-migration-local.json')
        chain.add_paragraph(local['human_review'])
    chain.save(ROOT / 'human/project-review.tex')
    compile_pdf(ROOT / 'human/project-review.tex')
    progress = {'completed_packages': completed, 'remaining_packages': remaining,
                'root_migration_complete': complete, 'findings': findings}
    (ROOT / 'agent/normalization-progress.json').write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    label = 'chained review only' if args.chain_only else f'{args.task_id} LaTeX/PDF and chained review'
    print(f'WROTE {label}; {len(remaining)} packages remain')


if __name__ == '__main__':
    main()
