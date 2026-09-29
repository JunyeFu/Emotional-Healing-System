"""Check preserved originals and actual neutral writing consumers."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
ARCHIVE = TASK / 'archive/signed-candidate'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def normalized(data):
    text = data.decode('utf-8-sig')
    text = '\n'.join(line.rstrip() for line in text.replace('\r\n', '\n').split('\n'))
    return (text if text.endswith('\n') else text + '\n').encode('utf-8')


def test_archived_bytes_and_candidate_input_manifest():
    for name, expected in read(TASK / 'inputs/sources.json')['archive_bytes'].items():
        assert hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest().upper() == expected
    old = TASK / 'archive/task-input'
    for entry in read(old / 'package_manifest.json')['files']:
        assert hashlib.sha256((old / entry['path']).read_bytes()).hexdigest() == entry['byte_sha256']
    assert len(list(old.rglob('*.*'))) == 4


def test_historical_sources_and_outputs_use_declared_hash_policy():
    evidence = read(ARCHIVE / 'evidence.json')
    assert evidence['hash_policy'] == 'UTF8_LF_TRAILING_WHITESPACE_REMOVED_FINAL_LF'
    candidate = read(GOV / 'u12_upgrade/acceptance/U12-07.json')['candidate_commit']
    for source in evidence['sources']:
        original = subprocess.check_output(['git', 'show', f"{candidate}:{source['name']}"], cwd=ROOT)
        assert hashlib.sha256(normalized(original)).hexdigest().upper() == source['sha256_declared']
    differences = []
    for output in evidence['outputs']:
        raw = (ARCHIVE / output['name']).read_bytes()
        historical_path = (GOV / 'u12_upgrade/U12-07_neutral_core_draft' / output['name']).relative_to(ROOT).as_posix()
        candidate_bytes = subprocess.check_output(['git', 'show', f'{candidate}:{historical_path}'], cwd=ROOT)
        assert raw.replace(b'\r\n', b'\n') == candidate_bytes.replace(b'\r\n', b'\n')
        legacy = '\n'.join(line.rstrip() for line in raw.decode('utf-8-sig').replace('\r\n', '\n').split('\n')).encode('utf-8')
        assert hashlib.sha256(legacy).hexdigest().upper() == output['sha256']
        if hashlib.sha256(normalized(raw)).hexdigest().upper() != output['sha256']:
            differences.append(output['name'])
    assert differences == ['design_method.md', 'sources.md']
    documented = read(TASK / 'evidence/historical-hash-policy.json')
    assert documented['outputs_without_final_lf'] == differences


def test_original_signatures_and_business_registration_not_rewritten():
    value = read(TASK / 'outputs/current-writing.json')
    signature = read(GOV / 'u12_upgrade/acceptance/U12-07.json')
    assert signature['candidate_commit'] == value['historical_candidate_commit']
    assert signature['signature_commit'] == value['historical_signature_commit']
    for kind in ('independent_review', 'human_review'):
        report = signature[kind]
        raw = (ROOT / report['report_path']).read_bytes()
        assert hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() == report['sha256_lf']
        assert report['status'] == 'PASS'
    for path in ('u12_upgrade/acceptance/U12-07.json', 'u12_upgrade/U12-07_第二人审核报告_已签署.md'):
        old = subprocess.check_output(['git', 'show', f'HEAD:{(GOV / path).relative_to(ROOT).as_posix()}'], cwd=ROOT)
        assert normalized(old) == normalized((GOV / path).read_bytes())
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-07')
    assert row['status'] == value['business_status'] == 'DONE'
    assert row['claimant'] == 'Codex(Grip)/小彬' and row['reviewer'] == '傅钧烨'
    assert row['depends_on'].split('|') == value['depends_on']
    assert value['new_independent_review'] == 'NOT_RUN' and value['new_human_acceptance'] == 'NOT_SIGNED'


@pytest.mark.parametrize('field,expected', [
    ('primary_outcome', 'panas_negative_affect_post_adjusted_for_pre'),
    ('contrast', 'native_minus_abstract'), ('negative_favors', 'scene_native'),
    ('positive_favors', 'abstract_pacer'), ('functional_guard_blocks_primary_reporting', False),
    ('scci_blocks_primary_reporting', False), ('equivalence_confirmatory_enabled', False),
    ('not_significant_is_equivalent', False), ('native_is_hidden', False),
    ('weather_breath_independent_effect', False), ('requires_unstarted_stage3_done', False),
    ('actual_partial_extension_must_be_disclosed', True), ('formal_n', None), ('formal_margin', None),
    ('real_results', 'NOT_RUN'), ('real_manuscript', 'NOT_DELIVERED'),
])
def test_current_reporting_contract(field, expected):
    assert read(TASK / 'outputs/current-writing.json')[field] == expected


def test_current_specifications_match_protocol_and_actual_measurement():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    value = read(TASK / 'outputs/current-writing.json')
    assert protocol['primary']['outcome'] == value['primary_outcome']
    assert protocol['functional_guard']['blocks_affect_reporting'] is False
    assert protocol['equivalence']['confirmatory_enabled'] is False
    measurement = read(ROOT / 'agent/tasks/U12-02/outputs/current-measurement.json')
    assert measurement['item_count'] == 8 and measurement['measurement_validity'] == 'PENDING'
    method = (TASK / 'outputs/current-method.md').read_text(encoding='utf-8')
    assert 'RQ1：' in method and 'PANAS负性情绪' in method
    assert '非论文正文' in method and '前测必须在其之前' in method
    tables = (TASK / 'outputs/table-spec.md').read_text(encoding='utf-8')
    assert len(re.findall(r'^\| T\d{2} \|', tables, re.M)) == value['table_count'] == 11
    assert 'T03 | PANAS主要比较' in tables and 'T04 | 机会PF功能护栏' in tables
    rules = (TASK / 'outputs/reporting-rules.md').read_text(encoding='utf-8')
    for phrase in ('CI全负', 'CI全正', 'CI跨零', '确认性等效默认未启用', 'PF任一分析集失败', '仅部分运行'):
        assert phrase in rules
    assert '投稿句式' in rules and 'NOT_RUN' in rules


def test_actual_consumers_sources_navigation_and_frozen_inputs():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file(), path
    for task in ('W-01', 'W-02'):
        filename = 'current-paper.md' if task == 'W-01' else 'current-manuscript.md'
        text = (ROOT / f'agent/tasks/{task}/outputs/{filename}').read_text(encoding='utf-8')
        assert 'U12-07' in text and '规格' in text and '原' in text
    for source in read(ROOT / 'agent/tasks/A-05/inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for path in (GOV / 'u12_upgrade/U12-07_neutral_core_draft/README.md',
                 ROOT / '00-项目管理/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-07/README.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / link).resolve().is_file()
    dispatch = GOV / '当前解锁独立任务包'
    for path in dispatch.rglob('*'):
        if path.is_file():
            relative = path.relative_to(ROOT).as_posix()
            old = subprocess.check_output(['git', 'rev-parse', f'HEAD:{relative}'], cwd=ROOT).strip()
            actual = subprocess.check_output(['git', 'hash-object', '--path', relative, relative], cwd=ROOT).strip()
            assert old == actual, path
    for path in [TASK / 'TASK.md', *(TASK / 'outputs').glob('*.md')]:
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
