"""Normalize project-owned directory names and their current consumers."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'agent/repository-layout.json'
MOVES = {
    'agent/modules/01-数据采集': 'agent/modules/acquisition',
    'agent/modules/02-信号处理': 'agent/modules/signal-processing',
    'agent/modules/03-TouchDesigner': 'agent/modules/touchdesigner',
    'agent/modules/04-Unity视觉': 'agent/modules/unity',
    'agent/modules/05-通信协议': 'agent/modules/communication',
    'agent/modules/06-MCP开发桥接': 'agent/modules/development-bridge',
    'agent/modules/07-数据治理': 'agent/modules/data-governance',
    'agent/modules/08-随机化': 'agent/modules/randomization',
    'agent/modules/运行准入': 'agent/modules/admission',
    'agent/design/情绪天气方案': 'agent/design/weather',
    'agent/governance/01-项目章程与规划': 'agent/governance/planning',
    'agent/governance/03-进度跟踪': 'agent/governance/progress',
    'agent/governance/04-风险管理': 'agent/governance/risks',
    'agent/governance/05-质量门禁': 'agent/governance/quality',
    'agent/governance/看板与进度': 'agent/governance/boards',
    'agent/governance/项目规约': 'agent/governance/charter',
}
TEXT = {'.md', '.py', '.ps1', '.json', '.csv', '.txt', '.toml', '.yaml',
        '.yml', '.ini', '.xml', '.tex', '.cs', '.shader', '.asmdef', '.uss',
        '.uxml', '.unity', '.asset', '.meta', '.svg', '.drawio', '.html', '.js'}
PRESERVED = {'archive', 'evidence', 'acceptance', 'baseline', 'external_source',
             'sources', '90_既有执行材料', '当前解锁独立任务包', 'mcp_td_v147'}


def relocate(path: str) -> str:
    for old, new in MOVES.items():
        if path == old or path.startswith(old + '/'):
            return new + path[len(old):]
    return path


def files() -> list[str]:
    output = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    return sorted({p.decode('utf-8') for p in output.split(b'\0') if p})


def preserved(path: str) -> bool:
    parts = Path(path).parts
    return bool(set(parts) & PRESERVED) or (
        'inputs' in parts and not path.endswith('/inputs/sources.json')) or any(
            marker in Path(path).name for marker in ('已签署', '审核报告', '验收记录')) or (
        path.startswith('agent/work/') and Path(path).name not in {
            'codex-blackboard.md', 'codex-verification-log.md'}) or Path(path).name in {
                '05_可领取任务包.csv', '12_独立任务包文件映射_v1.0.json',
                'legacy_evidence_binding.json', 'legacy-byte-observations.json'}


def rewrite(text: str, old: str, new: str) -> str:
    def link(match):
        target, sep, fragment = match.group(1).partition('#')
        target = target.removeprefix('<').removesuffix('>')
        if not target or target.startswith(('https:', 'http:', 'mailto:')):
            return match.group(0)
        absolute = (ROOT / old).parent / unquote(target)
        absolute = absolute.resolve()
        original_absolute = absolute
        previous = json.loads((ROOT / 'agent/root-layout.json').read_text(encoding='utf-8'))['entries']
        for entry in previous:
            old_parts = Path(entry['old']).parts
            for index in range(len(absolute.parts) - len(old_parts) + 1):
                if absolute.parts[index:index + len(old_parts)] == old_parts:
                    candidate = ROOT / entry['new'] / Path(*absolute.parts[index + len(old_parts):])
                    candidate = ROOT / relocate(candidate.relative_to(ROOT).as_posix())
                    if candidate.exists():
                        absolute = candidate
                    break
        if not absolute.exists():
            for anchor in ('agent', 'human'):
                for index, part in enumerate(absolute.parts):
                    if part == anchor:
                        candidate = ROOT / Path(*absolute.parts[index:])
                        if candidate.exists():
                            absolute = candidate
                            break
        if not absolute.is_relative_to(ROOT):
            return match.group(0)
        mapped = relocate(absolute.relative_to(ROOT).as_posix())
        root_relative = old.startswith(('agent/governance/', 'agent/modules/')) and mapped.startswith('agent/tasks/')
        if root_relative:
            relative = os.path.relpath(ROOT, (ROOT / new).parent).replace('\\', '/') + '/' + mapped
            return '](' + relative + sep + fragment + ')'
        if absolute == original_absolute and mapped == absolute.relative_to(ROOT).as_posix() and old == new:
            return match.group(0)
        return '](' + os.path.relpath(ROOT / mapped, (ROOT / new).parent).replace('\\', '/') + sep + fragment + ')'

    text = re.sub(r'\]\(([^)]+)\)', link, text)
    if Path(old).suffix == '.md':
        text = text.replace('agent/agent/', 'agent/').replace('human/human/', 'human/')
        previous = json.loads((ROOT / 'agent/root-layout.json').read_text(encoding='utf-8'))['entries']
        for entry in previous:
            text = re.sub(r'(?<=[\'\"`])' + re.escape(entry['old']) + '/',
                          lambda match: entry['new'] + '/', text)
    for source, target in MOVES.items():
        text = text.replace(source, target).replace(source.replace('/', '\\'), target.replace('/', '\\'))
        source_name, target_name = source.rsplit('/', 1)[1], target.rsplit('/', 1)[1]
        # These names are project-owned path components, including split Path expressions.
        text = re.sub(r'(?<![\w\u4e00-\u9fff])' + re.escape(source_name) + r'(?=[./\\\'\"`])',
                      lambda match: target_name, text)
    return text


def repair():
    report = json.loads(PLAN.read_text(encoding='utf-8'))
    excluded = {'agent/tools/resolve_frozen_source.py', 'agent/tools/normalize_repository_layout.py'}
    dirty = {'human/project/README.md', 'agent/work/codex-blackboard.md',
             'agent/work/codex-verification-log.md',
             'agent/tasks/T-01/execution/capture_workbench.py',
             'agent/tasks/T-01/execution/capture_workbench_sdk.py'}
    updated = 0
    for item in report['files']:
        old, new = item['old'], item['new']
        if not item['content_updated'] or old in excluded:
            continue
        result = subprocess.run(['git', 'show', 'HEAD:' + old], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode or old in dirty:
            continue
        original = result.stdout.decode('utf-8')
        content = original if preserved(old) else rewrite(original, old, new)
        (ROOT / new).write_bytes(content.encode('utf-8'))
        item['content_updated'] = content != original
        item['category'] = category(old)
        updated += 1
    report['current_consumers_updated'] = sum(p['content_updated'] for p in report['files'])
    save(PLAN, report)
    print(f'Repaired {updated} consumers; preserved registry and signed originals')


def refresh():
    report = json.loads(PLAN.read_text(encoding='utf-8'))
    changed = 0
    for item in report['files']:
        path = ROOT / item['new']
        if preserved(item['old']) or path.suffix not in TEXT or path.name == Path(__file__).name or item['old'] in {
            'agent/root-layout.json', 'agent/normalization-relocations.json', 'agent/repository-layout.json'}:
            continue
        text = path.read_text(encoding='utf-8')
        content = rewrite(text, item['new'], item['new'])
        if content != text:
            path.write_bytes(content.encode('utf-8'))
            item['content_updated'] = True
            changed += 1
    report['current_consumers_updated'] = sum(p['content_updated'] for p in report['files'])
    save(PLAN, report)
    print(f'Updated {changed} remaining path consumers')


def repair_bindings():
    bindings = json.loads(subprocess.check_output(
        ['git', 'show', 'HEAD:agent/normalization-relocations.json'], cwd=ROOT).decode('utf-8-sig'))
    for binding in bindings['frozen_sources']:
        binding['new_project_path'] = relocate(binding['new_project_path'])
        binding['impact_path'] = relocate(binding['impact_path'])
    existing = {(b['task_id'], b['old_project_path']) for b in bindings['frozen_sources']}
    for manifest in (ROOT / 'agent/governance').glob('**/当前解锁独立任务包/*/package_manifest.json'):
        data = json.loads(manifest.read_text(encoding='utf-8-sig'))
        for source in data['source_files']:
            key = (data['task_id'], source['source_path'])
            if key in existing:
                continue
            bindings['frozen_sources'].append({
                'task_id': key[0], 'old_project_path': key[1],
                'new_project_path': (manifest.parent / source['package_path']).relative_to(ROOT).as_posix(),
                'preserve_ready_dispatch': True, 'impact_path': 'human/project/repository-layout.md',
                'reason': 'Preserve original dispatch bytes after directory normalization.'})
    save(ROOT / 'agent/normalization-relocations.json', bindings)
    report = json.loads(PLAN.read_text(encoding='utf-8'))
    for item in report['files']:
        if Path(item['old']).name in {'legacy_evidence_binding.json', 'legacy-byte-observations.json'}:
            original = subprocess.check_output(['git', 'show', 'HEAD:' + item['old']], cwd=ROOT)
            (ROOT / item['new']).write_bytes(original)
            item['content_updated'] = False
            item['category'] = 'preserved-source-or-evidence'
    report['current_consumers_updated'] = sum(p['content_updated'] for p in report['files'])
    save(PLAN, report)
    print('Restored recorded frozen identities and normalized only their current targets')


def check():
    report = json.loads(PLAN.read_text(encoding='utf-8'))
    missing = [p['new'] for p in report['files'] if not (ROOT / p['new']).is_file()]
    targets = [p['new'].casefold() for p in report['files']]
    assert len(targets) == len(set(targets)), 'Destination collision'
    assert not missing, missing
    for move in report['moves']:
        assert not (ROOT / move['old']).exists(), move['old']
        assert (ROOT / move['new']).is_dir(), move['new']
    print(f"PASS {len(targets)} classified files, {len(report['moves'])} physical moves, no lost files or collisions")


def category(path: str) -> str:
    if path.startswith('agent/local/'):
        return 'local-runtime'
    if preserved(path):
        return 'preserved-source-or-evidence'
    if path.startswith('human/'):
        return 'reader-document-or-deliverable'
    if path.startswith('agent/modules/'):
        return 'implementation'
    if path.startswith('agent/tasks/'):
        return 'task-execution-or-handover'
    if path.startswith('agent/'):
        return 'project-maintenance'
    return 'repository-configuration'


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--repair', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--repair-bindings', action='store_true')
    args = parser.parse_args()
    if args.repair:
        repair()
        return
    if args.refresh:
        refresh()
        return
    if args.check:
        check()
        return
    if args.repair_bindings:
        repair_bindings()
        return
    paths = files()
    edits = {}
    for relative in paths:
        path = ROOT / relative
        if not path.is_file() or preserved(relative) or relative in {
            'agent/tools/normalize_repository_layout.py', 'agent/root-layout.json',
            'agent/normalization-relocations.json', 'agent/repository-layout.json'}:
            continue
        if path.suffix.lower() not in TEXT and path.name not in {'.gitignore', '.gitattributes'}:
            continue
        raw = path.read_bytes()
        if b'\0' in raw:
            continue
        try:
            original = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        result = rewrite(original, relative, relocate(relative))
        if result != original:
            edits[relative] = result
    for old, new in MOVES.items():
        if not (ROOT / old).is_dir() or (ROOT / new).exists():
            raise ValueError(f'Move requires unique source and empty target: {old} -> {new}')
    report = {
        'schema_version': 1, 'date': '2026-10-13',
        'status': 'APPLIED' if args.apply else 'PLANNED',
        'moves': [{'old': old, 'new': new} for old, new in MOVES.items()],
        'files': [{'old': p, 'new': relocate(p), 'category': category(p),
                   'content_updated': p in edits} for p in paths],
        'current_consumers_updated': len(edits),
        'naming': {'directories': 'lowercase semantic kebab-case',
                   'python': 'existing importable snake_case names',
                   'documents': 'README.md entry; descriptive Chinese or existing versioned title',
                   'preserved': 'task IDs, frozen inputs, signed evidence, third-party and native asset names'},
    }
    if args.apply:
        bindings_path = ROOT / 'agent/normalization-relocations.json'
        bindings = json.loads(bindings_path.read_text(encoding='utf-8'))
        for binding in bindings['frozen_sources']:
            binding['new_project_path'] = relocate(binding['new_project_path'])
            binding['impact_path'] = relocate(binding['impact_path'])
        existing = {(b['task_id'], b['old_project_path']) for b in bindings['frozen_sources']}
        # Dispatch snapshots already contain the exact frozen bytes; bind their recorded paths.
        for manifest in (ROOT / 'agent/governance').glob('**/当前解锁独立任务包/*/package_manifest.json'):
            data = json.loads(manifest.read_text(encoding='utf-8-sig'))
            for source in data['source_files']:
                key = (data['task_id'], source['source_path'])
                if key in existing:
                    continue
                snapshot = manifest.parent / source['package_path']
                if not snapshot.is_file():
                    raise ValueError(f'Missing dispatch snapshot: {snapshot}')
                bindings['frozen_sources'].append({
                    'task_id': key[0], 'old_project_path': key[1],
                    'new_project_path': relocate(snapshot.relative_to(ROOT).as_posix()),
                    'preserve_ready_dispatch': True,
                    'impact_path': 'human/project/repository-layout.md',
                    'reason': 'Resolve frozen input bytes from the existing dispatch snapshot after directory normalization.'})
        for old, new in MOVES.items():
            shutil.move(str(ROOT / old), str(ROOT / new))
        for relative, content in edits.items():
            (ROOT / relocate(relative)).write_bytes(content.encode('utf-8'))
        save(bindings_path, bindings)
        root_layout_path = ROOT / 'agent/root-layout.json'
        root_layout = json.loads(root_layout_path.read_text(encoding='utf-8'))
        for entry in root_layout['entries']:
            entry['new'] = relocate(entry['new'])
        save(root_layout_path, root_layout)
    save(PLAN, report)
    print(json.dumps({'status': report['status'], 'classified_files': len(paths),
                      'moves': len(MOVES), 'moved_files': sum(relocate(p) != p for p in paths),
                      'updated_consumers': len(edits)}))


if __name__ == '__main__':
    main()
