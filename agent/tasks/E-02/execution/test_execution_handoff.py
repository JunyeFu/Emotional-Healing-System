"""Validate Level B handoff facts, not real participant results."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
Q02 = ROOT / 'agent/tasks/Q-02/outputs'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def current():
    return read(TASK / 'outputs/current-execution.json')


def test_registry_and_actual_external_scope():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['task_id']: row for row in csv.DictReader(stream)}
    value = current()
    assert value['business_status'] == registry['E-02']['status'] == 'BLOCKED_EXTERNAL'
    assert value['dependencies'] == registry['E-02']['depends_on'].split('|')
    assert not registry['E-02']['claimant'] and not registry['E-02']['reviewer']
    assert registry['Q-02']['status'] == 'WAIT_DEP'
    assert registry['E-01']['status'] == 'BLOCKED_EXTERNAL'
    assert registry['U12-05']['status'] == 'WAIT_DEP_EXTERNAL'
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        record = next(row for row in csv.DictReader(stream) if row['capability_id'] == value['activity_capability'])
    assert record['status'] == value['activity_capability_status'] == 'PENDING_EXTERNAL'
    assert not record['evidence_ref'] and not value['requires_entire_g05_done']


def test_numbers_do_not_silently_freeze_old_plan():
    value = current()
    source = read(Q02 / 'current-level-b.json')['sample_plan']
    for field in ('frozen_total', 'frozen_per_condition', 'frozen_per_round'):
        assert value[field] is source[field] is None
    assert value['registry_people_range'] == source['e02_registry_people_range'] == [12, 16]
    assert value['historical_f02_total_range'] == source['historical_f02_total_range'] == [24, 32]
    assert value['sample_plan_status'] == source['status'] == 'CONFLICT_REQUIRES_RESEARCH_FREEZE'
    assert not value['closure_rules_frozen'] and value['observed_coverage'] == []


@pytest.mark.parametrize('field', [
    'one_condition_per_person', 'one_core_experience_per_person',
    'repeat_exposure_for_revision_allowed', 'formative_only_data_is_affect_trial_data',
    'question_timing', 'thinking_aloud_in_core', 'understanding_blocks_affect_reporting',
    'guesses_drop_valid_panas',
])
def test_timing_and_reporting_match_material_owner(field):
    assert current()[field] == read(Q02 / 'current-level-b.json')[field]


def test_actual_training_order_and_unmeasured_mastery():
    training = read(ROOT / 'agent/tasks/U12-03/outputs/contract.json')
    steps = training['timeline']
    assert steps.index('panas_pre') < steps.index('allocation_reveal') < steps.index('condition_training')
    assert steps.index('condition_training') < steps.index('core_800s') < steps.index('panas_post')
    assert training['formal_training_budget_seconds'] is None and not training['formal_collection_allowed']
    assert current()['time_to_mastery_seconds'] is None
    assert current()['time_to_mastery_reason'] == 'NOT_MEASURED'


@pytest.mark.parametrize('name,required', [
    ('responses.csv', {'response_status', 'response_started_ns', 'response_ended_ns', 'help_count',
                       'help_duration_ns', 'probe_duration_ns', 'material_version', 'clip_ref', 'build_ref'}),
    ('revisions.csv', {'coder_1', 'coder_2', 'disagreement', 'denominator', 'severity', 'decision',
                       'paired_check_ref', 'old_version', 'new_version', 'retest_ref', 'owner'}),
])
def test_real_templates_remain_blank_and_not_copied(name, required):
    with (Q02 / name).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        assert required <= set(reader.fieldnames)
        assert list(reader) == []
    assert not (TASK / 'outputs' / name).exists()
    changed = subprocess.run(['git', 'diff', 'HEAD', '--', str(Q02 / name)], cwd=ROOT,
                             capture_output=True, check=True)
    assert not changed.stdout


@pytest.mark.parametrize('name', ['00_第8步计划.md', '01_详细执行方案.md'])
def test_archive_original_bytes_and_navigation(name):
    expected = read(TASK / 'inputs/sources.json')['archived_bytes'][name]
    assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == expected
    entry = PLAN / '09_步骤08_LevelB认知预试' / name
    links = re.findall(r'\]\(([^)]+)\)', entry.read_text(encoding='utf-8'))
    assert links
    for link in links:
        assert (entry.parent / link).resolve().exists(), link


def test_current_sources_and_remaining_real_conditions():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).exists(), source
    value = current()
    assert value['claimant'] is value['reviewer'] is value['execution_owner'] is value['freeze_owner'] is None
    assert value['coding_owners'] == [] and value['real_closed_build'] is None
    assert value['real_activity'] == value['new_unity_regression'] == value['new_independent_review'] == 'NOT_RUN'
    assert value['new_human_acceptance'] == 'NOT_SIGNED'


def test_current_prose_preserves_observed_failures_without_fake_closure():
    text = (TASK / 'TASK.md').read_text(encoding='utf-8') + (TASK / 'outputs/current-execution.md').read_text(encoding='utf-8')
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
    for term in ('新修订轮使用新人', '不能填零', '双人', '原分歧', 'null/NOT_MEASURED',
                 'FORMATIVE_TRAINING_ONLY', '交互状态估计', '不预填PASS或DONE'):
        assert term in text
