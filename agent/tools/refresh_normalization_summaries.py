"""Update current normalization facts without changing business acceptance."""
import csv
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from resolve_frozen_source import resolve_project_path, resolve_source

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
REPORT = ROOT / 'agent/evidence/normalization-summary-refresh.json'
CURRENT = '根目录19/19项已迁入human/agent，当前读取和运行入口已验证，业务签收不变'
SHARED = {
    '后续整体迁至agent/modules时修复消费者': '已迁至agent/modules且消费者已验证',
    '共享工程待全包后实际收拢': '共享工程已迁入agent/modules并验证运行入口',
    '本包状态不变，规范化不是根目录迁移完成': '本包业务状态不变；根目录迁移已落实，研究接线仍由对应任务完成',
    'apply_governance、freeze_legacy_evidence和共享验证仍有活跃测试，待整体迁移处理': 'apply_governance、freeze_legacy_evidence和共享验证已随治理目录迁移，活跃测试及消费者已验证',
    '共享实现仍在原模块目录，': '共享实现已位于agent/modules，',
    'Unity共享工程和历史签署仍在原业务目录，等待全项目统一迁移': 'Unity共享工程已位于agent/modules，历史签署原件保留且消费者已修正',
    '共享采集模块暂留技术目录，后续统一迁至Agent模块并修复消费者': '共享采集模块已位于agent/modules，消费者已修正',
    '共享实现仍在技术模块，': '共享实现已位于agent/modules，',
    '共享随机化/测量及P-02模块仍是唯一原位置，': '共享随机化、测量及P-02实现均以agent/modules为唯一权威位置，',
    '共享历史业务目录暂留，': '共享历史来源已随治理目录迁入Agent层，',
    '共享业务模块仍为原权威入口，': '共享业务模块以agent/modules为当前权威入口，',
    '共享实现保留在原模块目录，': '共享实现位于agent/modules，',
    '共享实现与旧签收仍在原业务目录，': '共享实现和旧签收均已迁入Agent层，',
    '共享原材料暂留原位置，最终模块迁移时修复引用': '共享原材料已随模块归属迁入Agent层，引用已修正',
    '共享TD/Python源码暂留原模块，最终整体迁移': '共享TD/Python源码位于agent/modules，不复制到任务包',
    '共享模块和全项目根目录收拢仍待后续，不把七包整理当成全仓迁移完成': CURRENT,
    '共享模块和根目录整体迁移仍待后续逐包处理': CURRENT,
    '共享TD/Python模块及根目录业务目录仍待全部包完成后的整体迁移': CURRENT,
    '其他包、共享模块和根目录双层迁移仍待继续': CURRENT,
    '其余共享模块和根目录业务内容仍待整体双层迁移': CURRENT,
    '共享业务模块和旧根目录仍待整体迁移': CURRENT,
    '研究原件、共享治理与工程保持当前归属；任务整理后仍须整体迁入双层并修运行路径': '研究原件保持历史字节，共享治理和工程已迁入Agent层且当前运行路径已验证',
    '根目录旧业务仍需全包后实际迁移，当前共享文件改说明不等于根迁移完成': CURRENT,
    '其余旧工具、共享模块与根目录双层迁移仍待后续': CURRENT,
    '全部旧根目录的物理迁移仍是整体目标的下一项': CURRENT,
    '全部共享业务目录仍待收拢到人类层/Agent层，': '全部共享业务目录已实际迁入人类层/Agent层，',
    '根目录共享运行模块仍待整体归入Agent模块；本包归档和Word并不完成全部根目录物理迁移': CURRENT,
    '根目录全部业务目录迁入human/agent尚未结束': CURRENT,
    '不冒充根目录已迁移': '根目录迁移的完成依据本轮19项实际验证，不改变业务状态',
    '随后参加整体根目录迁移': CURRENT,
    '后续整体根目录迁移时移动和修复，不复制新的活动实现': '已随agent/governance实际迁移并修复，不复制新的活动实现',
    '整体根目录迁移时统一处理，不复制并行业务目录': CURRENT,
    '工程与根目录旧业务归属仍待最终统一迁移': CURRENT,
    '71/71逐包规范化完成后仍须把旧根目录实际迁入human/agent并修运行引用、生成器及冻结输入消费者': '71/71逐包整理和19/19物理迁移已落实，当前运行、生成器及冻结输入消费者经验证',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fix_directory(text):
    text = text.replace('.artifacts-local', 'agent/local/artifacts')
    for old, new in SHARED.items():
        text = text.replace(old, new)
    # Only the current directory/progress sections are rewritten, never signed sources.
    text = text.replace(CURRENT, '@CURRENT_MIGRATION@')
    text = re.sub(
        r'(?:最后整体|整体|最终|全项目|共享|整个|全部|全)?根目录[^。；\n]{0,50}'
        r'(?:尚未完成|仍未完成|未完成|尚未结束|未结束|仍须|仍需|需处理|再修复|待|继续|统一更新引用|将连同)'
        r'[^。；\n]*', '@CURRENT_MIGRATION@', text)
    text = text.replace('@CURRENT_MIGRATION@', CURRENT)
    return text


def preserve_dispatch(changed, report):
    mapping_path = ROOT / 'agent/normalization-relocations.json'
    mapping = read(mapping_path)
    bindings = []
    def canonical(data):
        return b'\n'.join(line.rstrip(b' \t') for line in data.replace(b'\r\n', b'\n').split(b'\n'))
    for manifest_path in GOV.glob('当前解锁独立任务包/*/package_manifest.json'):
        manifest = read(manifest_path)
        for item in manifest['source_files']:
            current = resolve_project_path(ROOT, item['source_path']).relative_to(ROOT).as_posix()
            if current not in changed:
                continue
            selected = resolve_source(ROOT, manifest['task_id'], manifest['status'], item['source_path'])
            if selected != ROOT / current:
                continue
            snapshot = (manifest_path.parent / item['package_path']).read_bytes()
            original = subprocess.check_output(['git', 'show', report['baseline_commit'] + ':' + current], cwd=ROOT)
            assert canonical(snapshot) == canonical(original), current
            assert hashlib.sha256(canonical(snapshot)).hexdigest().upper() == item['sha256'], current
            target = 'agent/archive/normalization-summary-inputs/' + manifest['task_id'] + '/' + current
            path = ROOT / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(snapshot)
            entry = {'task_id': manifest['task_id'], 'old_project_path': item['source_path'],
                     'new_project_path': target, 'preserve_ready_dispatch': True,
                     'impact_path': 'agent/evidence/normalization-summary-impact.md',
                     'reason': 'Preserve received input while current normalization progress text is refreshed.'}
            mapping['frozen_sources'].append(entry)
            bindings.append(entry)
    save(mapping_path, mapping)
    report['dispatch_bindings_preserved'] = bindings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refine', action='store_true', help='Reapply reviewed text rules to this batch baseline only')
    args = parser.parse_args()
    if REPORT.exists() and not args.refine:
        raise ValueError('Summary refresh is already recorded; do not overwrite its baseline')
    layout = read(ROOT / 'agent/root-layout.json')
    assert len(layout['entries']) == 19 and all(e['status'] == 'MIGRATED' for e in layout['entries'])
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['task_id']: row for row in csv.DictReader(stream)}
    existing = read(REPORT) if args.refine else None
    baseline = existing['baseline_commit'] if existing else subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    report = {'baseline_commit': baseline,
              'scope': 'Current normalization facts only; business conclusions and historical acceptance unchanged',
              'summaries': [], 'current_documents': [], 'migration_findings_closed': []}
    for task_id, row in registry.items():
        path = ROOT / f'agent/tasks/{task_id}/outputs/summary.json'
        summary = json.loads(subprocess.check_output(['git', 'show', baseline + ':' + path.relative_to(ROOT).as_posix()], cwd=ROOT)) if args.refine else read(path)
        original = json.loads(json.dumps(summary))
        for section in summary['sections']:
            if section['heading'] == '目录与文件整理':
                section['paragraphs'] = [fix_directory(p) for p in section['paragraphs']]
            if section['heading'] == '收尾与下一包':
                section['paragraphs'] = [
                    '规范化71/71包、根目录迁移19/19项完成；每包Word由Agent源生成。',
                    f"业务状态{row['status']}，原签收与未交付项不变；后续按注册表和实际依赖推进。",
                ]
        for finding in summary.get('findings', []):
            if finding['status'] in {'OPEN_ROOT_MIGRATION', 'OPEN_PROJECT_MIGRATION'}:
                report['migration_findings_closed'].append({'task_id': task_id, 'id': finding['id']})
                finding.update(status='FIXED_PHYSICAL_ROOT_MIGRATION_AND_RUNTIME_CHECKS',
                               description='19项根目录已实际迁入双层，当前运行消费者及Word来源经验证；业务状态不变',
                               source='agent/evidence/root-migration-check.json')
            elif finding.get('source'):
                source = resolve_project_path(ROOT, finding['source'])
                if source.is_relative_to(ROOT) and source.exists():
                    finding['source'] = source.relative_to(ROOT).as_posix()
        summary['next_task'] = '按业务注册表及实际依赖推进'
        assert summary['conclusion'] == original['conclusion']
        assert summary['historical_acceptance'] == original['historical_acceptance']
        save(path, summary)
        report['summaries'].append({'task_id': task_id, 'path': path.relative_to(ROOT).as_posix(),
                                    'business_status': row['status'], 'historical_acceptance_preserved': True})
    for task in (ROOT / 'agent/tasks').iterdir():
        for path in [task / 'TASK.md', *task.glob('outputs/current-*.md')]:
            if not path.is_file():
                continue
            original = subprocess.check_output(['git', 'show', baseline + ':' + path.relative_to(ROOT).as_posix()], cwd=ROOT).decode('utf-8-sig') if args.refine else path.read_text(encoding='utf-8-sig')
            lines = original.splitlines(keepends=True)
            for i, line in enumerate(lines):
                if any(word in line for word in ('根目录', '原业务目录', '暂留原位置', '暂留原模块')):
                    if path.name == 'current-scope.md' and '规范化入口此前' in line:
                        lines[i] = '当前71/71包已整理，根目录19/19项已实际迁移；本次文本同步不改变真实任务状态。\n'
                    elif path.name == 'current-freeze.md' and '不把70/71' in line:
                        lines[i] = '本包真实冻结、独立复核、机构批准及第二人仍未完成，WAIT_DEP_EXTERNAL保留。71/71包整理与19/19根目录迁移不等于项目业务DONE。\n'
                    else:
                        lines[i] = fix_directory(line)
                elif '共享TD/Python源码暂留' in line or '待整体迁移处理' in line:
                    lines[i] = fix_directory(line)
            updated = ''.join(lines)
            if updated != original:
                path.write_text(updated, encoding='utf-8')
                report['current_documents'].append(path.relative_to(ROOT).as_posix())
            elif args.refine and path.relative_to(ROOT).as_posix() in existing['current_documents']:
                path.write_text(original, encoding='utf-8')
    changed = {entry['path'] for entry in report['summaries']} | set(report['current_documents'])
    if args.refine:
        report['dispatch_bindings_preserved'] = existing['dispatch_bindings_preserved']
    else:
        preserve_dispatch(changed, report)
    save(REPORT, report)
    print(f"Refreshed {len(report['summaries'])} summaries, {len(report['current_documents'])} current documents; closed {len(report['migration_findings_closed'])} physical migration findings")


if __name__ == '__main__':
    main()
