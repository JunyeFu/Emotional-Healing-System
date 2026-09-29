"""Record scoped path repairs and preserve existing dispatch input identities."""
import hashlib
import json
from pathlib import Path
import runpy
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'agent/evidence'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    helper = runpy.run_path(str(ROOT / 'agent/tools/migrate_support_roots.py'))
    # Only these thin wrappers are current navigation, not signed design sources.
    wrappers = ('07-数据治理/docs/formal_machine_setup.md',
                '07-数据治理/docs/formal_environment_closure_runbook.md',
                '03-TouchDesigner/TD原型规划.md', '03-TouchDesigner/step-3-breath-animation.md')
    for relative in wrappers:
        old = ROOT / '02-技术研发' / relative
        current = ROOT / 'agent/modules' / relative
        text = current.read_text(encoding='utf-8')
        def relocate(relative_path):
            return relative_path.replace('02-技术研发/', 'agent/modules/', 1) if relative_path.startswith('02-技术研发/') else relative_path
        helper['rewrite_links'].__globals__['relocate'] = relocate
        # The first wrapper was repaired explicitly before this step.
        links = re.findall(r'\]\(([^)]+)\)', text)
        if any(not (current.parent / link).resolve().exists() for link in links if not link.startswith('http')):
            current.write_text(helper['rewrite_links'](text, old, current), encoding='utf-8')
    manual_path = EVIDENCE / 'root-migration-modules-manual.json'
    manual = read(manual_path)
    manual['files'] += ['agent/modules/' + p for p in wrappers]
    manual['files'] += ['agent/modules/tests/session_core/conftest.py', 'agent/modules/tests/session_store/conftest.py']
    manual['files'] = sorted(set(manual['files']))
    save(manual_path, manual)
    mapping_path = ROOT / 'agent/normalization-relocations.json'
    mapping = read(mapping_path)
    for entry in mapping['frozen_sources']:
        if entry['new_project_path'].startswith('agent/archive/root-migration/modules-inputs/'):
            entry['preserve_ready_dispatch'] = True
    source = 'agent/tasks/P-01/execution/generate_golden_trace.py'
    manifests = list((ROOT / 'agent/governance').glob('**/当前解锁独立任务包/T-02/package_manifest.json'))
    assert len(manifests) == 1
    manifest = manifests[0]
    item = next(row for row in read(manifest)['source_files'] if row['source_path'] == source)
    snapshot = (manifest.parent / item['package_path']).read_bytes()
    baseline = read(EVIDENCE / 'root-migration-modules-originals.json')['baseline_commit']
    previous = subprocess.check_output(['git', 'show', baseline + ':' + source], cwd=ROOT)
    def canonical(content):
        return b'\n'.join(line.rstrip(b' \t') for line in content.replace(b'\r\n', b'\n').split(b'\n'))
    assert canonical(previous) == canonical(snapshot)
    assert hashlib.sha256(canonical(snapshot)).hexdigest().upper() == item['sha256']
    original_path = 'agent/archive/root-migration/modules-inputs/p01-golden-generator.py'
    (ROOT / original_path).write_bytes(snapshot)
    binding = {'task_id': 'T-02', 'old_project_path': source,
               'new_project_path': original_path, 'preserve_ready_dispatch': True,
               'impact_path': 'agent/evidence/root-migration-modules-impact.md',
               'reason': 'Preserve the received generator input while its live module import path is repaired.'}
    if binding not in mapping['frozen_sources']:
        mapping['frozen_sources'].append(binding)
    save(mapping_path, mapping)
    captures = read(EVIDENCE / 'root-migration-modules-originals.json')['files']
    preserved = read(EVIDENCE / 'root-migration-modules-inputs.json')['bindings']
    hashes = {entry['old']: entry['sha256'] for entry in captures}
    for entry in preserved:
        assert hashlib.sha256((ROOT / entry['new_project_path']).read_bytes()).hexdigest() == hashes[entry['old_project_path']]
    print('PASS original dispatch bytes:', len(preserved), 'module bindings and P-01 generator')


if __name__ == '__main__':
    main()
