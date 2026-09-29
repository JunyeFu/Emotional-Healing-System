"""Candidate classifier and current handoff; no observed research effects."""
import csv
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
SOURCE = ROOT / 'agent/governance/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/sources/unpacked/SRP_Final_Upgrade_v1.2_2026-09-08/03_工具与验证/result_classifier.py'
spec = importlib.util.spec_from_file_location('u1210_classifier', TASK / 'execution/result_classifier.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Evidence, classify = module.Evidence, module.classify


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


CASES = read(TASK / 'inputs/classifier-cases.json')['cases']


@pytest.mark.parametrize('case', CASES, ids=lambda row: row['id'])
def test_fixed_synthetic_cases(case):
    result = classify(Evidence(**case['evidence']))
    assert result['direction_evidence'] == case['direction']
    assert result['practical_scale'] == case['scale']
    assert result['formal_equivalence_claim_allowed'] is False
    assert result['automatic_deployment_recommendation'] is False
    assert result['mechanism_or_all_explicit_vs_native_claim_allowed'] is False
    assert result['prespecified_affect_result_must_be_reported'] is True


@pytest.mark.parametrize('change', [
    {'estimate': float('nan')}, {'ci_high': float('inf')}, {'ci_low': float('-inf')},
    {'estimate': True}, {'ci_low': False}, {'estimate': '0'}, {'estimate': None},
    {'ci_low': 2, 'ci_high': -2}, {'ci_low': 0, 'ci_high': 0}, {'estimate': 2},
    {'ci_level': 0.90}, {'ci_level': True}, {'practical_delta': 0}, {'practical_delta': -1},
    {'practical_delta': float('nan')}, {'practical_delta': True},
    {'affect_assessable': 'false'}, {'delivery_valid': 1},
    {'functional_guard': 'APPROVED_BY_AI'}, {'sensitivity': 'PASS'},
])
def test_invalid_boundary_inputs_rejected(change):
    args = {'estimate': 0, 'ci_low': -1, 'ci_high': 1}
    args.update(change)
    with pytest.raises(ValueError):
        classify(Evidence(**args))


def test_multiaxis_labels_do_not_suppress_affect_or_enable_equivalence():
    result = classify(Evidence(3, 2, 4, 1, delivery_valid=False, functional_guard='FAIL', sensitivity='SENSITIVE'))
    assert result['direction_evidence'] == 'ABSTRACT_LOWER'
    assert result['interpretation_scope'] == 'DELIVERY_VALIDITY_LIMITED'
    assert result['functional_guard'] == 'FAIL' and result['sensitivity'] == 'SENSITIVE'
    assert result['prespecified_affect_result_must_be_reported'] is True
    narrow = classify(Evidence(0, -.2, .2, 1))
    assert narrow['practical_scale'] == 'WITHIN_PRESPECIFIED_PRACTICAL_BOUNDS'
    assert narrow['direction_evidence'] == 'NO_DIRECTION_ESTABLISHED'
    assert narrow['formal_equivalence_claim_allowed'] is False


def test_source_copy_and_three_archived_input_identities():
    assert SOURCE.read_bytes() == (TASK / 'archive/source-tool/result_classifier.py').read_bytes()
    original = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
    active = ast.parse((TASK / 'execution/result_classifier.py').read_text(encoding='utf-8-sig'))
    for name in ('Evidence', '_number', 'classify'):
        before = next(node for node in original.body if getattr(node, 'name', None) == name)
        after = next(node for node in active.body if getattr(node, 'name', None) == name)
        assert ast.dump(before) == ast.dump(after), name
    archive = TASK / 'archive/task-input'
    manifest = read(archive / 'package_manifest.json')
    assert manifest['input_snapshot_id'] == 'ac08cfbb94c2e048198b717d6099cc7660a3ee3382e9de871720968c25d8824d'
    assert manifest['dispatch_allowed'] is False
    for item in manifest['files']:
        assert hashlib.sha256((archive / item['path']).read_bytes()).hexdigest() == item['byte_sha256']


def test_current_registry_real_inputs_still_not_delivered():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-10')
    assert row['status'] == 'WAIT_DEP' and row['depends_on'] == 'A-05'
    assert row['claimant'] == row['reviewer'] == '' and row['effort_person_days'] == '2'
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['primary']['contrast'] == 'native_minus_abstract'
    assert protocol['primary']['minimum_important_affect_difference'] is None
    assert protocol['formal_participant_collection_allowed'] is False
    actual = read(ROOT / 'agent/tasks/A-05/outputs/current-analysis.json')
    assert actual['result_classifier'] == 'U12-10_CANDIDATE_ONLY_FORMAL_NOT_DELIVERED'
    assert actual['real_data_analysis'] == 'NOT_RUN'
    assert actual['research_lock_id'] is actual['formal_sap_ref'] is None
    empty = read(ROOT / 'agent/tasks/A-05/outputs/analysis-report-template.json')
    assert all(empty['primary'][key] is None for key in ('beta', 'ci_lower', 'ci_upper', 'p_value', 'n'))


def test_generated_case_report_is_reproducible_and_only_synthetic(tmp_path):
    output = TASK / 'outputs/synthetic-classification.json'
    expected = output.read_bytes()
    run = subprocess.run([sys.executable, TASK / 'execution/run_cases.py'], cwd=ROOT, capture_output=True)
    assert run.returncode == 0, run.stderr
    assert output.read_bytes() == expected
    report = read(output)
    assert report['scope'] == 'SYNTHETIC_ONLY_NOT_RESEARCH_RESULTS'
    assert report['real_analysis'] == 'NOT_RUN' and report['formal_authorization'] is False
    assert len(report['cases']) == 15
    for row, case in zip(report['cases'], CASES):
        assert row == {'id': case['id'], 'result': classify(Evidence(**case['evidence']))}


def test_actual_cli_valid_invalid_json_and_missing_field(tmp_path):
    help_result = subprocess.run([sys.executable, TASK / 'execution/result_classifier.py', '--help'], capture_output=True)
    assert help_result.returncode == 0 and b'95 percent CI' in help_result.stdout
    path = tmp_path / 'case.json'
    for payload, code in [({'estimate': 3, 'ci_low': 2, 'ci_high': 4}, 0),
                          ({'estimate': 3, 'ci_low': 2, 'ci_high': 4, 'ci_level': .90}, 2),
                          ({'estimate': 3}, 2)]:
        path.write_text(json.dumps(payload), encoding='utf-8')
        result = subprocess.run([sys.executable, TASK / 'execution/result_classifier.py', path], capture_output=True)
        assert result.returncode == code
        if code == 0:
            assert json.loads(result.stdout)['direction_evidence'] == 'ABSTRACT_LOWER'
        else:
            assert b'Input rejected:' in result.stderr and not result.stdout
    path.write_text('{', encoding='utf-8')
    result = subprocess.run([sys.executable, TASK / 'execution/result_classifier.py', path], capture_output=True)
    assert result.returncode == 2 and not result.stdout


def test_sources_navigation_and_current_language():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / relative).is_file(), relative
    old = ROOT / 'agent/governance/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-10/README.md'
    assert not (old.parent / 'TASK.md').exists()
    for path in (old, TASK / 'TASK.md', TASK / 'outputs/current-classification.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if not link.startswith('https://') and not link.endswith('.docx'):
                assert (path.parent / link).resolve().exists(), (path, link)
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-classification.md', TASK / 'outputs/claim-rules.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
    assert '../../U12-10/outputs/current-classification.md' in (ROOT / 'agent/tasks/A-05/outputs/current-analysis.md').read_text(encoding='utf-8')
