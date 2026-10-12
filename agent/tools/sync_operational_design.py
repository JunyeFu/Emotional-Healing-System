"""Attach the operation-level design to its consumers; preserve business acceptance."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / 'agent/design/design-foundation-20261008'
BACKUP = ROOT / 'agent/local/artifacts/operational-design-20261008/before'
MARKER = '\n\n<!-- ODES-20261008 -->'


def backup(path):
    target = BACKUP / path.relative_to(ROOT)
    if path.is_file() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sync(task_ids=None):
    design = json.loads((DESIGN / 'operational-design.json').read_text(encoding='utf-8'))
    paths = [str((DESIGN / name).relative_to(ROOT).as_posix()) for name in design['sources']]
    for task, responsibility in design['consumers'].items():
        if task_ids is not None and task not in task_ids:
            continue
        norm = design.get('normalization')
        norm_text = ''
        if norm:
            owned = [key for key, value in design['parameter_specs'].items() if task in value['owner_tasks']]
            norm_text = ('NORM-20261008：普通学习间隙、不诱发压力、不按NA筛选；'
                         '校准前10/保留核验后10，正式冻结在前置验证之后。'
                         '设计材料已交付，M01唯一中文题本/映射/指令与M02使用条件仍未关闭。')
            if owned:
                norm_text += '本包承接参数规格：' + '、'.join(owned) + '；核对定义、单位、方法、接受依据和失败收缩，真实数值不由文档冻结。'
        folder = ROOT / 'agent/tasks' / task
        task_path = folder / 'TASK.md'
        backup(task_path)
        note = (MARKER + '\n## 操作级设计交接\n\n'
                + responsibility + '。本轮已交付设计规格、配对示意和实验候选，'
                + '不将它们称为真实运行、参数冻结、正式研究或新增业务签收。\n\n'
                + '[专项交接](outputs/operational-design-handoff.md)列出具体来源和未完成证据。\n')
        if norm:
            note += '\n## 规范化设计材料验收\n\n' + norm_text + '\n\n'
            note += '- [ ] ND1 核对本包专项材料与设计索引，能执行既定验证而无需重定构念/规则。\n'
            note += '- [ ] ND2 真实值、真实证据与设计完整分别标记；M01/M02不继承历史验收。\n'
        task_path.write_text(task_path.read_text(encoding='utf-8').split(MARKER)[0] + note, encoding='utf-8')
        handoff = '# ' + task + ' 操作级设计交接\n\n' + responsibility + '。\n\n'
        handoff += '设计候选ODES-20261008；本轮三项设计已交付，原业务状态、历史签收及领取输入保持。真实执行/复核仍按TASK验收，不继承历史通过。\n\n'
        for name in design['sources']:
            handoff += '- [' + name + '](../../../design/design-foundation-20261008/' + name + ')\n'
        handoff += '\n普通调整仅在周期边界；中断可即时撤下要求。X不能由G或画面补造；I达成、G跟随与调整成本分报。数值参数、可辨性、量表版本、关注差及N待真实校准/冻结。\n'
        if norm:
            handoff += '\n## 规范化材料与确定方法\n\n' + norm_text + '\n\n'
            for key in owned:
                spec = design['parameter_specs'][key]
                handoff += '### ' + spec['label'] + '\n\n'
                handoff += '标识 `' + key + '`；' + spec['definition_and_unit'] + '。' + spec['evidence_and_role'] + '。\n\n'
                handoff += '确定：' + spec['data_and_determination'] + '\n\n接受：' + spec['acceptance_rule'] + '\n\n失败：' + spec['failure_revision'] + '。\n\n'
        (folder / 'outputs/operational-design-handoff.md').write_text(handoff, encoding='utf-8')
        source_path = folder / 'inputs/sources.json'
        backup(source_path)
        source = json.loads(source_path.read_text(encoding='utf-8-sig'))
        source['paths'] = list(dict.fromkeys(source['paths'] + paths))
        source['operational_design_candidate'] = design['candidate_id']
        save(source_path, source)
        summary_path = folder / 'outputs/summary.json'
        backup(summary_path)
        summary = json.loads(summary_path.read_text(encoding='utf-8-sig'))
        summary['operational_design_candidate'] = design['candidate_id']
        summary['sections'][2]['paragraphs'] = [x for x in summary['sections'][2]['paragraphs'] if not x.startswith('ODES-20261008设计交付：')]
        summary['sections'][2]['paragraphs'].append('ODES-20261008设计交付：' + responsibility + '；设计文件和示意已交付，真实执行及独立复核仍待完成。')
        if norm:
            summary['normalization_candidate'] = norm['id']
            summary['normalization_design_closed'] = norm['design_closed']
            summary['sections'][2]['paragraphs'] = [x for x in summary['sections'][2]['paragraphs'] if not x.startswith('NORM-20261008：')]
            summary['sections'][2]['paragraphs'].append(norm_text)
        existing = {x['path'] for x in summary.get('source_links', [])}
        for path in paths:
            if path not in existing:
                summary.setdefault('source_links', []).append({'path': path, 'label': '操作设计 ' + Path(path).name})
        save(summary_path, summary)
        for current in (folder / 'outputs').glob('current*.md'):
            if 'implementation-evidence' in current.name:
                continue
            backup(current)
            current.write_text(current.read_text(encoding='utf-8').split(MARKER)[0] + MARKER + '\n\n操作级设计已交付；本包具体责任见[专项交接](operational-design-handoff.md)，真实运行与复核仍待执行。\n' + ('\n' + norm_text + '\n' if norm else ''), encoding='utf-8')
    if task_ids is None or 'F-02' in task_ids:
        from refresh_f02_measurement import refresh
        refresh()
    print('Attached operation-level design to ' + str(sum(task_ids is None or task in task_ids for task in design['consumers'])) + ' task consumers.')


if __name__ == '__main__':
    sync()
