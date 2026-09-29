"""Capture and verify the final local-material moves without publishing private files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'agent/evidence/root-migration-local.json'
MOVES = {
    '_archive': 'agent/archive/local',
    '_worktrees': 'agent/local/worktrees',
    'tmp': 'agent/local/tmp',
    '.tools': 'agent/local/tools',
    '.artifacts-local': 'agent/local/artifacts',
    '.pytest_cache': 'agent/local/pytest-cache',
}
CONSUMERS = (
    'agent/tasks/T-01/execution/verify.py',
    'agent/tasks/T-01/execution/run_td_probe.py',
    'agent/tasks/T-01/execution/repair_readonly_layout.py',
    'agent/tasks/U-02/execution/generate_demo.ps1',
    'agent/tasks/U-02/TASK.md',
    'agent/tasks/U-02/outputs/current-adapter-contract.md',
    'agent/tasks/U-05/execution/verify.py',
    'agent/tasks/U-06/execution/verify.py',
    'agent/tasks/U-08/execution/verify.py',
)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inventory(path):
    files = [p for p in path.rglob('*') if p.is_file()]
    return {'files': len(files), 'bytes': sum(p.stat().st_size for p in files)}


def write(report):
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def capture():
    if REPORT.exists():
        raise ValueError('Original inventory already captured')
    entries = []
    lfs = json.loads(subprocess.check_output(['git', 'lfs', 'ls-files', '--json'], cwd=ROOT))['files']
    by_name = {item['name']: item for item in lfs}
    names = subprocess.check_output(['git', 'ls-files', '-z', '--', *MOVES], cwd=ROOT).decode('utf-8').split('\0')
    for name in filter(None, names):
        path = ROOT / name
        old = next(key for key in MOVES if name.startswith(key + '/'))
        target = MOVES[old] + name[len(old):]
        sha = digest(path)
        entry = by_name[name]
        if sha != entry['oid'] or path.stat().st_size != entry['size']:
            raise ValueError('LFS original does not match its pointer: ' + name)
        entries.append({'old': name, 'new': target, 'sha256': sha, 'bytes': entry['size']})
    write({'scope': 'Physical local-directory moves; original tracked media bytes and private aggregate inventory',
           'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
           'directories': [{'old': old, 'new': new, **inventory(ROOT / old)} for old, new in MOVES.items()],
           'tracked_originals': entries, 'verified': False})
    print(f'Captured {len(entries)} tracked LFS originals and {len(MOVES)} local directories')


def repair():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    repaired = []
    for name in CONSUMERS:
        path = ROOT / name
        data = path.read_bytes()
        updated = data.replace(b'.artifacts-local', b'agent/local/artifacts').replace(b'.tools/ffmpeg', b'agent/local/tools/ffmpeg')
        if data != updated:
            path.write_bytes(updated)
            repaired.append(name)
    layout_path = ROOT / 'agent/root-layout.json'
    layout = json.loads(layout_path.read_text(encoding='utf-8'))
    for entry in layout['entries']:
        if entry['old'] in MOVES:
            if (ROOT / entry['old']).exists() or not (ROOT / entry['new']).exists():
                raise ValueError('Move is not complete: ' + entry['old'])
            entry['status'] = 'MIGRATED'
            entry['evidence'] = REPORT.relative_to(ROOT).as_posix()
    layout_path.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report['current_consumers_repaired'] = repaired
    write(report)
    print(f'Repaired {len(repaired)} current consumers; completion remains unproven')


def verify():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    for entry in report['directories']:
        if (ROOT / entry['old']).exists():
            raise ValueError('Old local root remains: ' + entry['old'])
        actual = inventory(ROOT / entry['new'])
        if actual != {key: entry[key] for key in ('files', 'bytes')}:
            raise ValueError('Local inventory drift: ' + entry['new'])
    for entry in report['tracked_originals']:
        path = ROOT / entry['new']
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('Original bytes changed: ' + entry['new'])
    for name in CONSUMERS:
        text = (ROOT / name).read_text(encoding='utf-8-sig')
        if '.artifacts-local' in text or '.tools/ffmpeg' in text:
            raise ValueError('Unrepaired current consumer: ' + name)
    report['verified'] = True
    report['human_review'] = (
        f"六类本机目录已实际迁入Agent层，{len(report['tracked_originals'])}件已跟踪样片逐字节保留；"
        '本机历史、工具、缓存和其他QA材料仍不发布。历史媒体配置通过当前读取入口解析新位置，不改原件或业务签收。'
    )
    write(report)
    print(f"PASS six local moves and {len(report['tracked_originals'])} original LFS media")


def preserve_inputs():
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    mapping_path = ROOT / 'agent/normalization-relocations.json'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    bindings = []
    def canonical(data):
        return b'\n'.join(line.rstrip(b' \t') for line in data.replace(b'\r\n', b'\n').split(b'\n'))
    for manifest_path in (ROOT / 'agent/governance').glob('**/当前解锁独立任务包/*/package_manifest.json'):
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for item in manifest['source_files']:
            source = item['source_path']
            if source not in CONSUMERS:
                continue
            snapshot = (manifest_path.parent / item['package_path']).read_bytes()
            baseline = subprocess.check_output(['git', 'show', report['baseline_commit'] + ':' + source], cwd=ROOT)
            if canonical(snapshot) != canonical(baseline):
                raise ValueError('Received input differs from original baseline: ' + source)
            if hashlib.sha256(canonical(snapshot)).hexdigest().upper() != item['sha256']:
                raise ValueError('Received snapshot hash changed: ' + source)
            target = 'agent/archive/root-migration/local-inputs/' + manifest['task_id'] + '/' + source
            path = ROOT / target
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != snapshot:
                raise ValueError('Preserved original already exists with different bytes')
            path.write_bytes(snapshot)
            binding = {'task_id': manifest['task_id'], 'old_project_path': source,
                       'new_project_path': target, 'preserve_ready_dispatch': True,
                       'impact_path': 'agent/evidence/root-migration-local-impact.md',
                       'reason': 'Keep received input bytes while current local-tool paths are relocated.'}
            if binding not in mapping['frozen_sources']:
                mapping['frozen_sources'].append(binding)
            bindings.append(binding)
    report['dispatch_bindings_preserved'] = bindings
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write(report)
    print(f'Preserved {len(bindings)} received input bindings without regenerating dispatch packages')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('capture', 'repair', 'verify', 'preserve_inputs'))
    globals()[parser.parse_args().operation]()
