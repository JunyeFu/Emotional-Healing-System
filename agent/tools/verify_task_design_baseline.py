"""Verify the current task plan, historical boundaries and dispatch design supplements."""
from pathlib import Path
import csv
import json
import re

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
BASELINE = ROOT / 'agent/design/design-foundation-20261008/task-baseline.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify():
    data = read(BASELINE)
    with (GOV/'05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 71 and {r['task_id'] for r in rows} == set(data['tasks'])
    links = 0
    for row in rows:
        task = row['task_id']
        item = data['tasks'][task]
        folder = ROOT/'agent/tasks'/task
        assert row['status'] == item['recorded_status'], (task, 'original status changed')
        assert row['design_baseline_id'] == data['baseline_id']
        assert row['design_revision_state'] == item['revision_state']
        assert row['current_acceptance_criteria'] == '；'.join(item['acceptance_criteria'])
        assert row['current_deliverables'] == ';'.join(item['deliverables'])
        assert row['current_evidence_required'] == ';'.join(item['evidence_required'])
        assert row['current_completion_condition'] == item['completion_condition']
        task_text = (folder/'TASK.md').read_text(encoding='utf-8')
        assert all(x in task_text for x in item['acceptance_criteria']), task
        assert data['baseline_id'] in task_text
        assert all('- [ ] '+x in task_text for x in item['acceptance_criteria']), (task,'new AC inherited pass')
        summary = read(folder/'outputs/summary.json')
        old = read(folder/'archive/pre-design-baseline-20261008/summary.json')
        assert summary['historical_acceptance'] == old['historical_acceptance'], (task,'historical review changed')
        assert summary['design_baseline_id'] == data['baseline_id']
        assert summary['sections'][1]['paragraphs'] == item['acceptance_criteria']
        revision = read(folder/'outputs/design-revision.json')
        assert revision['baseline_id'] == data['baseline_id'] and revision['formal_collection_allowed'] is False
        assert revision['acceptance_criteria'] == item['acceptance_criteria']
        source = read(folder/'inputs/sources.json')
        assert BASELINE.relative_to(ROOT).as_posix() in source['paths']
        for path in source['paths']:
            assert (ROOT/path).exists(), (task,path)
        for current in (folder/'outputs').glob('current*.md'):
            if 'implementation-evidence' not in current.name:
                text = current.read_text(encoding='utf-8')
                assert all(x in text for x in item['acceptance_criteria']), current
        paths = [folder/'TASK.md', *(folder/'outputs').glob('current*.md')]
        for path in paths:
            for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
                if '://' in target or target.startswith('#'):
                    continue
                target = target.strip('<>')
                resolved = path.parent / target.split('#')[0]
                assert resolved.exists(), (task,path.name,target)
                links += 1
    dispatch = GOV/'当前解锁独立任务包'
    for row in rows:
        task = row['task_id']
        if row['status'] not in {'READY','IN_PROGRESS','IN_REVIEW'}:
            continue
        manifest = read(dispatch/task/'package_manifest.json')
        assert manifest['design_baseline_id'] == data['baseline_id']
        assert manifest['current_scope_acceptance'] == 'PENDING_NOT_INHERITED_FROM_ORIGINAL_REVIEW'
        assert len(manifest['design_updates']) >= 10
        if row['status'] in {'IN_PROGRESS','IN_REVIEW'}:
            impact = read(GOV/'audit_upgrade/input_impacts'/f'{task}_design-baseline-20261008.json')
            assert manifest['input_snapshot_id'] == impact['retained_input_snapshot_id']
            assert manifest.get('candidate_identity') == impact['candidate_identity']
        text = (dispatch/task/'TASK.md').read_text(encoding='utf-8')
        for criterion in data['tasks'][task]['acceptance_criteria']:
            assert '- [ ] '+criterion in text, (task,'new dispatch AC prechecked')
        assert 'design_updates/' in text
    print(f'PASS: 71 current plans, original statuses/signatures, 5 dispatch scopes, 3 frozen claims; {links} current document links')

if __name__ == '__main__':
    verify()
