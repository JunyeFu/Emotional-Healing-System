"""Generate current human reviews from task execution summaries."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def document(title):
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.7)
    section.left_margin = section.right_margin = Inches(0.8)
    for name in ('Normal', 'Title', 'Heading 1', 'Heading 2'):
        style = doc.styles[name]
        style.font.name = 'Microsoft YaHei'
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
    doc.styles['Normal'].font.size = Pt(10.5)
    doc.styles['Normal'].paragraph_format.space_after = Pt(7)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.15
    for style in doc.styles:
        for border in list(style.element.iter(qn('w:pBdr'))):
            border.getparent().remove(border)
    doc.styles['Title'].font.size = Pt(21)
    doc.styles['Heading 1'].font.size = Pt(13)
    doc.add_paragraph(title, 'Title')
    footer = section.footer.paragraphs[0]
    footer.add_run('SRP 任务包审阅  ')
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    return doc


def render_summary(summary, output):
    doc = document(summary['title'])
    doc.add_paragraph(f"审阅日期 {summary['review_date']}    任务 {summary['task_id']}")
    numbering = ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一')
    for index, section in enumerate(summary['sections']):
        if index in (3, 7):
            doc.add_page_break()
        doc.add_heading(f"{numbering[index]} {section['heading']}", level=1)
        if index == 0:
            doc.add_paragraph(summary['conclusion'])
        for paragraph in section['paragraphs']:
            doc.add_paragraph(paragraph)
        if index == 8:
            acceptance = summary['historical_acceptance']
            doc.add_paragraph(f"历史审核人 {acceptance['reviewer']}    日期 {acceptance['date']}")
            if acceptance.get('commit'):
                doc.add_paragraph(f"历史审核提交 {acceptance['commit']}")
            doc.add_paragraph(acceptance['method'])
    for source in summary.get('source_links', []):
        paragraph = doc.add_paragraph()
        link = OxmlElement('w:hyperlink')
        relationship = doc.part.relate_to(
            (ROOT / source['path']).resolve().as_uri(),
            'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
            is_external=True,
        )
        link.set(qn('r:id'), relationship)
        run = OxmlElement('w:r')
        text = OxmlElement('w:t')
        text.text = source['label']
        run.append(text)
        link.append(run)
        paragraph._p.append(link)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)


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
    args = parser.parse_args()
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    registry = {r['task_id']: r for r in rows}
    summary = check_task(args.task_id, registry)
    if args.check:
        review = ROOT / 'human/tasks' / args.task_id / 'summary.docx'
        if not review.is_file():
            raise ValueError(f'Missing human summary: {args.task_id}')
        if review.is_file():
            text = '\n'.join(p.text for p in Document(review).paragraphs)
            expected = [summary['conclusion']]
            if summary['historical_acceptance'].get('commit'):
                expected.append(summary['historical_acceptance']['commit'])
            expected.extend(p for s in summary['sections'] for p in s['paragraphs'])
            if any(value not in text for value in expected):
                raise ValueError(f'Word content drift: {args.task_id}')
        print(f'PASS package structure and sources: {args.task_id}')
        return
    render_summary(summary, ROOT / 'human/tasks' / args.task_id / 'summary.docx')
    chain = document('SRP 任务包串联审阅')
    chain.add_paragraph('本文件由已整理包的Agent层总结串联生成。用于检查任务完成范围和下游交接；未整理包不推定已核验。')
    completed = []
    findings = []
    for row in rows:
        path = ROOT / 'agent/tasks' / row['task_id'] / 'outputs/summary.json'
        if not path.exists():
            continue
        item = check_task(row['task_id'], registry)
        completed.append(row['task_id'])
        chain.add_heading(f"{row['task_id']} {row['domain']}", level=1)
        chain.add_paragraph(item['conclusion'])
        handoff = next(s for s in item['sections'] if s['heading'] == '上下游交接')
        for paragraph in handoff['paragraphs']:
            chain.add_paragraph(paragraph)
        for finding in item['findings']:
            findings.append({'task_id': row['task_id'], **finding})
            chain.add_paragraph(f"{finding['id']} {finding['status']}：{finding['description']}")
    chain.add_heading('待整理队列', level=1)
    remaining = [r['task_id'] for r in rows if r['task_id'] not in completed]
    next_task = remaining[0] if remaining else '目录整体迁移'
    count = chain.add_paragraph(f"已整理{len(completed)}包，待整理{len(remaining)}包；根目录双层迁移未完成。下一项{next_task}。")
    count.paragraph_format.keep_with_next = True
    queue = chain.add_paragraph('、'.join(remaining))
    queue.paragraph_format.keep_together = True
    chain.save(ROOT / 'human/project-review.docx')
    progress = {'completed_packages': completed, 'remaining_packages': remaining,
                'root_migration_complete': False, 'findings': findings}
    (ROOT / 'agent/normalization-progress.json').write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'WROTE {args.task_id} Word and chained review; {len(remaining)} packages remain')


if __name__ == '__main__':
    main()
