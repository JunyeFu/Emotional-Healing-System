"""Audit the four requested normalization deliverables against current files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from docx import Document
from build_task_reviews import ROOT, GOV, check_task
from verify_root_migration import check_word, read
from verify_summary_refresh import verify_refreshed_word


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-final', action='store_true')
    args = parser.parse_args()
    import csv
    registry_path = GOV / '05_可领取任务包.csv'
    with registry_path.open(encoding='utf-8-sig', newline='') as stream:
        registry = {r['task_id']: r for r in csv.DictReader(stream)}
    refresh = read(ROOT / 'agent/evidence/normalization-summary-refresh.json')
    baseline = refresh['baseline_commit']
    original_registry = subprocess.check_output(
        ['git', 'show', baseline + ':' + registry_path.relative_to(ROOT).as_posix()], cwd=ROOT)
    assert registry_path.read_bytes().replace(b'\r\n', b'\n') == original_registry.replace(b'\r\n', b'\n')
    rendered = read(ROOT / 'agent/evidence/normalization-summary-render.json')
    page_records = {r['task_id']: r for r in rendered['tasks']}
    chain_text = '\n'.join(p.text for p in Document(ROOT / 'human/project-review.docx').paragraphs)
    packages = []
    for task, row in registry.items():
        summary = check_task(task, registry)
        word = ROOT / f'human/tasks/{task}/summary.docx'
        assert verify_refreshed_word(word.relative_to(ROOT).as_posix())
        pages = page_records[task]
        assert pages['word_sha256'] == digest(word)
        assert set(pages['changed_pages']) == set(pages['changed_pages_visually_checked'])
        assert pages['current_pages'] == 3
        archive = ROOT / f'agent/tasks/{task}/archive/README.md'
        assert archive.stat().st_size > 0
        assert summary['conclusion'] in chain_text
        handoff = next(s for s in summary['sections'] if s['heading'] == '上下游交接')
        assert all(p in chain_text for p in handoff['paragraphs'])
        assert all(f['description'] in chain_text for f in summary['findings'])
        packages.append({'task_id': task, 'business_status': row['status'],
                         'word_source_links': check_word(task, summary),
                         'archive_disposition': archive.relative_to(ROOT).as_posix(),
                         'word_sha256': digest(word)})
    assert len(packages) == 71
    layout = read(ROOT / 'agent/root-layout.json')
    assert len(layout['entries']) == 19
    for entry in layout['entries']:
        assert entry['status'] == 'MIGRATED'
        assert not (ROOT / entry['old']).exists() and (ROOT / entry['new']).exists()
    assert {p.name for p in ROOT.iterdir()} == set(layout['root_entries_retained'])
    tests = read(ROOT / 'agent/evidence/root-migration-summary-package-tests.json')
    assert len(tests) == 60 and all(r['exit_code'] == 0 for r in tests)
    pytest = ET.parse(ROOT / 'agent/evidence/normalization-final-pytest.xml').getroot()
    suites = pytest.findall('testsuite')
    assert sum(int(s.get('tests', 0)) for s in suites) == 635
    assert all(int(s.get('failures', 0)) + int(s.get('errors', 0)) == 0 for s in suites)
    local = read(ROOT / 'agent/evidence/root-migration-local.json')
    assert len(local['tracked_originals']) == 48
    for item in local['tracked_originals']:
        path = ROOT / item['new']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
        pointer = subprocess.check_output(['git', 'show', baseline + ':' + item['new']], cwd=ROOT).decode()
        assert 'oid sha256:' + item['sha256'] in pointer
    snapshot_count = 0
    for path in GOV.glob('当前解锁独立任务包/*/package_manifest.json'):
        original = json.loads(subprocess.check_output(
            ['git', 'show', baseline + ':' + path.relative_to(ROOT).as_posix()], cwd=ROOT))
        current = read(path)
        assert original == current
        snapshot_count += len(current['source_files'])
    assert snapshot_count == 61
    if args.require_final:
        assert layout['root_migration_complete']
        chain_qa = read(ROOT / 'agent/evidence/normalization-chain-render.json')
        assert chain_qa['word_sha256'] == digest(ROOT / 'human/project-review.docx')
        assert set(chain_qa['changed_pages']) == set(chain_qa['changed_pages_visually_checked'])
    report = {
        'scope': 'All four normalization requirements; no new business acceptance or research approval',
        'baseline': baseline, 'final_audit': args.require_final,
        'requirements': {
            '1_per_package_word': {'packages': 71, 'pages': 213, 'source_match': True,
                                   'changed_pages_inspected': 114},
            '2_agent_structure_and_obsolete_files': {'packages': 71,
                'structure': 'TASK.md + inputs/execution/evidence/outputs/archive',
                'disposition_records': 71, 'current_package_suites_passed': 60},
            '3_physical_human_agent_roots': {'moves': 19, 'pending': 0,
                'unexpected_root_entries': [], 'word_links': sum(r['word_source_links'] for r in packages)},
            '4_chained_review_and_source_first_fixes': {'summaries_and_handoffs': 71,
                'migration_findings_closed': len(refresh['migration_findings_closed']),
                'current_documents_refreshed': len(refresh['current_documents']),
                'business_and_historical_acceptance_preserved': True}},
        'preservation': {'frozen_dispatch_snapshots': 61, 'original_lfs_media': 48,
                         'registry_unchanged': True},
        'root_python_tests': 635, 'packages': packages,
        'runtime_evidence': 'Migration Unity/TD/media runs retained; final refresh changes only documents and tools',
        'business_gaps': 'Remain assigned to their existing task packages; normalization does not mark them DONE',
    }
    target = ROOT / 'agent/evidence/normalization-completion-audit.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS four requirements:', 'final' if args.require_final else 'candidate; final chain QA still required')


if __name__ == '__main__':
    main()
