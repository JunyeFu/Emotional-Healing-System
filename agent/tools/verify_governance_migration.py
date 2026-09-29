"""Verify original governance bytes and current task Word link-only repairs."""
import hashlib
import argparse
import io
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'agent/evidence'
PLAN = 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/'
GOV = PLAN + '24_团队任务与项目治理/'
MANUAL = {
    GOV + name for name in (
        '13_render_ready_task_packages.py', '14_validate_ready_task_packages.py',
        '15_validate_audit_upgrade.py', 'governance_profile.py',
        'audit_upgrade/build_upgrade_evidence_manifest.py', 'u12_upgrade/validate_u12_governance.py',
        'u12_upgrade/freeze_legacy_evidence.py', 'u12_upgrade/apply_governance.py',
    )
} | {
    PLAN + '99_验证与清单/validate_team_tool_baseline.py',
    PLAN + '99_验证与清单/validate_protocol_authority_v1_1.py',
    'agent/governance/README.md',
}


def read(name):
    return json.loads((EVIDENCE / name).read_text(encoding='utf-8'))


def main():
    originals = read('root-migration-governance-originals.json')['files']
    repairs = read('root-migration-governance-repairs.json')
    allowed = set(repairs['current_files_repaired']) | MANUAL
    kept, changed = [], []
    for entry in originals:
        path = ROOT / entry['new']
        if (ROOT / entry['old']).exists() or not path.is_file():
            raise ValueError('Not a physical move: ' + entry['old'])
        if hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']:
            kept.append(entry['new'])
        elif entry['new'] in allowed:
            changed.append(entry['new'])
        else:
            raise ValueError('Undocumented original mutation: ' + entry['new'])
        protected = any(part in entry['new'] for part in (
            '/sources/', '/baseline/', '/external_source/', '/90_既有执行材料/',
            '/当前解锁独立任务包/', '/acceptance/',
        ))
        if protected and entry['new'] in changed:
            raise ValueError('Frozen or historical original changed: ' + entry['new'])
    word_links = 0
    for entry in repairs['word_relationships_repaired']:
        before = subprocess.run(['git', 'show', '3ddd7f3:' + entry['path']], cwd=ROOT,
                                stdout=subprocess.PIPE, check=True).stdout
        with ZipFile(io.BytesIO(before)) as original, ZipFile(ROOT / entry['path']) as current:
            if set(original.namelist()) != set(current.namelist()):
                raise ValueError('Word archive members changed')
            for name in original.namelist():
                if name != 'word/_rels/document.xml.rels' and original.read(name) != current.read(name):
                    raise ValueError('Word changed beyond current links: ' + entry['path'])
        word_links += entry['links']
    result = {'original_files': len(originals), 'unchanged_original_files': len(kept),
              'current_consumers_changed': changed, 'word_documents_checked': len(repairs['word_relationships_repaired']),
              'word_hyperlinks_relocated': word_links, 'word_body_and_other_parts_unchanged': True,
              'frozen_dispatch_signed_acceptance_and_external_sources_preserved': True}
    (EVIDENCE / 'root-migration-governance-preservation.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS {len(originals)} original files; {len(kept)} unchanged; {word_links} links in {result["word_documents_checked"]} unchanged Word bodies')


def package_tests(scope='governance'):
    prefix = f'root-migration-{scope}-package-tests'
    output = EVIDENCE / prefix
    output.mkdir(exist_ok=True)
    results = []
    for directory in sorted({p.parent for p in (ROOT / 'agent/tasks').glob('*/execution/test_*.py')}):
        result = subprocess.run(['py', '-3.14', '-m', 'pytest', '-q', str(directory)], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        task = directory.parent.name
        (output / (task + '.txt')).write_bytes(result.stdout)
        results.append({'task_id': task, 'exit_code': result.returncode})
        lines = result.stdout.decode('utf-8', 'replace').splitlines()
        print(task, result.returncode, lines[-1] if lines else '', flush=True)
    (EVIDENCE / (prefix + '.json')).write_text(
        json.dumps(results, indent=2) + '\n', encoding='utf-8')
    return int(any(item['exit_code'] for item in results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package-tests', action='store_true')
    parser.add_argument('--package-test-scope', choices=['governance', 'support'], default='governance')
    args = parser.parse_args()
    if args.package_tests:
        raise SystemExit(package_tests(args.package_test_scope))
    main()
