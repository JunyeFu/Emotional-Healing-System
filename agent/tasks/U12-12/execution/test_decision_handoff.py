"""Check current handoff facts without making a research or public decision."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_registry_scope_and_unassigned_roles():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-12')
    current = read(TASK / 'outputs/current-decision.json')
    assert row['status'] == current['business_status'] == 'WAIT_DEP_EXTERNAL'
    assert row['depends_on'].split('|') == current['depends_on'] == ['W-03', 'A-06']
    assert row['claimant'] == row['reviewer'] == ''
    assert current['claimant'] is current['reviewer'] is None


def test_original_input_identity_and_bytes():
    archive = TASK / 'archive/task-input'
    manifest = read(archive / 'package_manifest.json')
    assert manifest['dispatch_allowed'] is False
    assert manifest['input_snapshot_id'] == 'ebb1976ce87611c552eac2c9447bd899c1f75789047c4750689be1e3f39f3eb1'
    for item in manifest['files']:
        assert hashlib.sha256((archive / item['path']).read_bytes()).hexdigest() == item['byte_sha256']


def test_current_report_matches_actual_sources():
    spec = importlib.util.spec_from_file_location('u1212_inspect', TASK / 'execution/inspect_handoff.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.report() == read(TASK / 'outputs/current-decision.json')


def test_no_selected_winner_or_public_approval():
    value = read(TASK / 'outputs/current-decision.json')
    assert value['options'] == ['scene_native', 'abstract_pacer', 'retain_research_prototype']
    assert value['selected_option'] is value['decision_evidence_ref'] is None
    assert value['real_decision'] == 'NOT_MADE'
    assert value['real_scope_closure'] == 'NOT_RUN'
    assert value['author_consent'] == 'NOT_OBTAINED'
    assert value['candidate_release_commit'] is None
    assert value['clean_rebuild'] == 'NOT_RUN'
    for key in ('upstream_publication_authorized', 'public_release_authorized',
                'restricted_transfer_authorized', 'automatic_deployment_recommendation',
                'native_is_default_winning_product', 'normalization_is_business_completion',
                'root_migration_complete'):
        assert value[key] is False, key
    assert value['independent_review'] == 'NOT_RUN'
    assert value['human_acceptance'] == 'NOT_SIGNED'


def test_eight_real_handover_objects_remain_undelivered():
    items = read(TASK / 'outputs/current-decision.json')['eight_handover_items']
    assert items == read(ROOT / 'agent/tasks/W-04/outputs/handover-index.json')['items']
    assert len(items) == 8
    for item in items:
        assert item['status'] == 'NOT_DELIVERED'
        assert item['actual_path'] is item['byte_hash'] is item['receiver'] is None


def test_synthetic_comparisons_are_not_product_decisions():
    fixture = read(ROOT / 'agent/tasks/U12-10/outputs/synthetic-classification.json')
    assert fixture['scope'] == 'SYNTHETIC_ONLY_NOT_RESEARCH_RESULTS'
    assert fixture['real_analysis'] == 'NOT_RUN'
    assert len(fixture['cases']) == 15
    assert all(case['result']['automatic_deployment_recommendation'] is False for case in fixture['cases'])
    text = (TASK / 'outputs/publication-workbook.md').read_text(encoding='utf-8')
    rows = [line for line in text.splitlines() if line.startswith('|')]
    assert len(rows) - 2 == 12
    assert all('待决定' in row for row in rows[2:])


def test_active_sources_and_consumer_links():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for path in [TASK / 'TASK.md', *list((TASK / 'outputs').glob('*.md'))]:
        text = path.read_text(encoding='utf-8')
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
        for link in re.findall(r'\]\(([^)]+)\)', text):
            if not link.startswith('https://'):
                assert (path.parent / link).resolve().exists(), (path.name, link)
    consumer = (ROOT / 'agent/tasks/W-04/outputs/current-handover.md').read_text(encoding='utf-8')
    assert '../../U12-12/outputs/current-decision.md' in consumer
