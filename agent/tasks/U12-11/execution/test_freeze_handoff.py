"""Current parameter and source gaps, without approving or changing them."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def test_active_task_registration_and_direct_dependencies():
    actual = next(row for row in rows() if row['task_id'] == 'U12-11')
    value = read(TASK / 'outputs/current-freeze.json')
    assert actual['status'] == value['business_status'] == 'WAIT_DEP_EXTERNAL'
    assert actual['depends_on'].split('|') == [d['id'] for d in value['dependencies']] == ['G-05', 'E-03', 'U12-09', 'A-03-CAL']
    assert actual['claimant'] == actual['reviewer'] == '' and actual['effort_person_days'] == '2'
    assert value['claimant'] is value['reviewer'] is None
    assert all(dep['status'] != 'DONE' for dep in value['dependencies'])
    assert value['real_parameter_freeze'] == 'NOT_DELIVERED'
    assert value['formal_authorization'] is value['formal_gate_proved'] is value['root_migration_complete'] is False
    assert value['human_acceptance'] == 'NOT_SIGNED' and value['independent_review'] == 'NOT_RUN'


@pytest.mark.parametrize('index', [0, 1, 2])
def test_original_input_bytes_preserved(index):
    archive = TASK / 'archive/task-input'
    manifest = read(archive / 'package_manifest.json')
    entry = manifest['files'][index]
    assert hashlib.sha256((archive / entry['path']).read_bytes()).hexdigest() == entry['byte_sha256']
    assert manifest['input_snapshot_id'] == '872991f355d66bf818b42d811b5f43e9c7ef25239063af25978b4e67aa5c67fa'
    assert manifest['dispatch_allowed'] is False


def test_readonly_observation_rebuilds_actual_report():
    inspector = runpy.run_path(str(TASK / 'execution/inspect_freeze.py'))
    assert inspector['report']() == read(TASK / 'outputs/current-freeze.json')
    assert read(TASK / 'outputs/current-freeze.json')['scope'] == 'CURRENT_HANDOFF_INDEX_NOT_FREEZE_OR_APPROVAL'


def test_same_fifteen_freezes_no_shadow_approval_registry():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    report = read(TASK / 'outputs/current-freeze.json')
    index = read(ROOT / report['freeze_index_ref'])
    assert list(index['required_freezes']) == protocol['required_freezes']
    assert [row['id'] for row in report['required_freezes']] == protocol['required_freezes']
    assert len(report['required_freezes']) == 15
    assert all(row['status'] == 'PENDING' and row['evidence_ref'] is None for row in report['required_freezes'])
    text = (TASK / 'outputs/freeze-handoff.md').read_text(encoding='utf-8')
    for key in protocol['required_freezes']:
        assert f'| {key} |' in text
    assert index['preregistration_receipt_ref'] is index['calibration_receipt_ref'] is None
    assert index['formal_collection_allowed'] is index['downstream']['release_allowed'] is False


def test_candidate_numbers_are_not_formal_parameters():
    report = read(TASK / 'outputs/current-freeze.json')
    assert all(value is None for value in report['formal_parameters'].values())
    assert report['candidate_only'] == {'functional_margin': .075, 'imputations': 100, 'power_target': .9}
    assert report['old_anchors_not_final_power'] == [48, 192, 240]
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['equivalence']['confirmatory_enabled'] is False
    assert protocol['sequence']['allocation_block_size_candidate'] == 48
    assert protocol['sequence']['stage_1_balanced_sequences_per_arm'] == 24
    assert protocol['sequence']['completion_based_refilling_forbidden'] is True
    spec = read(ROOT / 'agent/tasks/U12-04/outputs/power_spec.json')
    assert not any(spec['frozen'][key] for key in ('n_frozen', 'effect_frozen', 'margin_frozen'))


def test_real_before_cal_and_cal_before_research_freeze():
    milestones = read(GOV / 'audit_upgrade/task_milestones_v1.2.json')['milestones']
    cal = next(item for item in milestones if item['id'] == 'A-03-CAL')
    assert cal['depends_on'] == ['A-03-REAL', 'E-03']
    assert {'G-03', 'U12-11'} <= set(cal['consumers'])
    states = read(GOV / 'audit_upgrade/task_milestone_status_v1.0.json')['statuses']
    assert states['A-03-SPEC'] == 'DONE' and states['A-03-REAL'] == states['A-03-CAL'] == 'WAIT_DEP'
    report = read(TASK / 'outputs/current-freeze.json')
    assert report['real_calibration_status'] == 'NOT_DELIVERED'
    assert report['real_technical_closeout'] == 'NOT_GENERATED'
    closeout = read(ROOT / 'agent/tasks/E-03/outputs/current-closeout.json')
    assert closeout['required_upstream_cal_milestone'] == 'REAL_NOT_FINAL_CAL'


@pytest.mark.parametrize('mutant,expected', [
    ('formal', 'FORMAL_COLLECTION_NOT_BLOCKED'),
    ('n', 'UNAPPROVED_NUMERIC_FREEZE'),
    ('equivalence', 'UNAPPROVED_NUMERIC_FREEZE'),
    ('drop_cal', 'CALIBRATION_MUST_PRECEDE_FREEZE'),
])
def test_existing_governance_negative_cases_not_new_approval_gate(mutant, expected):
    checker = runpy.run_path(str(GOV / 'u12_upgrade/validate_u12_governance.py'))['semantic_errors']
    registry = copy.deepcopy(rows())
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    if mutant == 'formal':
        protocol['formal_participant_collection_allowed'] = True
    elif mutant == 'n':
        protocol['sample_planning']['formal_randomized_n'] = 192
    elif mutant == 'equivalence':
        protocol['equivalence']['confirmatory_enabled'] = True
    else:
        next(row for row in registry if row['task_id'] == 'U12-11')['depends_on'] = 'G-05|E-03|U12-09'
    assert expected in checker(registry, protocol, read(GOV / 'audit_upgrade/task_milestones_v1.2.json'))


def test_five_stage1_qualifications_do_not_become_thirteen_global_done():
    report = read(TASK / 'outputs/current-freeze.json')
    assert [row['capability_id'] for row in report['stage1_capabilities']] == [
        'INSTITUTION_STAGE1', 'QUESTIONNAIRE_PERMISSION', 'RETENTION_AND_PRIVACY', 'FORMAL_MACHINE', 'STATION_CAPACITY_STAGE1']
    assert all(row['status'] == 'PENDING_EXTERNAL' and not row['evidence_ref'] for row in report['stage1_capabilities'])
    assert report['g05_all_capability_count'] == 13
    assert read(ROOT / 'agent/tasks/G-05/outputs/current-admission.json')['global_done_rule'] == 'ALL_13_QUALIFIED_CURRENT_GOVERNANCE'
    assert read(ROOT / 'agent/tasks/G-03/outputs/current-freeze.json')['g05_global_done_activity_scope_conflict'] == 'OPEN_GOVERNANCE_DECISION'


def test_800_seconds_not_whole_session_and_teaching_exposure_still_missing():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['core_experience']['recommended_total_seconds'] == 800
    assert protocol['training']['budget_seconds'] is None
    assert protocol['training']['condition_specific_training_after_panas_pre'] is True
    assert protocol['training']['primary_estimand_includes_condition_specific_training'] is True
    assert read(ROOT / 'agent/tasks/G-03/outputs/current-freeze.json')['first_condition_training_exposure_integrated'] is False
    text = (TASK / 'outputs/current-freeze.md').read_text(encoding='utf-8')
    assert '800秒仅四模块核心' in text and '不造可招募人数' in text


def test_current_sources_navigation_and_language():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / relative).is_file(), relative
    old = ROOT / 'agent/governance/01-项目章程与规划/2026-09-08_SRP_v1.2_当前基线适配包/tasks/U12-11/README.md'
    assert not (old.parent / 'TASK.md').exists()
    for path in (old, TASK / 'TASK.md', TASK / 'outputs/current-freeze.md', TASK / 'outputs/freeze-handoff.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if not link.startswith('https://') and not link.endswith('.docx'):
                assert (path.parent / link).resolve().exists(), (path, link)
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-freeze.md', TASK / 'outputs/freeze-handoff.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
    assert '../../U12-11/outputs/current-freeze.md' in (ROOT / 'agent/tasks/G-03/outputs/current-freeze.md').read_text(encoding='utf-8')
