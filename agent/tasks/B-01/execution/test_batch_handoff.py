"""Inspect the real Level C interfaces and blank batch handoff, not people."""
from collections import Counter
import csv
import json
from pathlib import Path
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / 'agent/modules'))
from srp_session_core.sequence import FixedSequenceProvider
from srp_session_core.models import AssignmentBundle
from srp_session_core.errors import SessionCoreError


def load(name):
    return json.loads((TASK / 'outputs' / name).read_text(encoding='utf-8'))


def test_template_registry_and_no_real_acceptance():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'B-01')
    value = load('current-batch.json')
    assert row['status'] == value['business_status'] == 'BLOCKED_EXTERNAL'
    assert row['kind'] == value['task_kind'] == 'TEMPLATE'
    assert row['depends_on'].split('|') == value['depends_on']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is value['historical_acceptance'] is None
    assert value['instances'] == [] and value['real_activity'] == 'NOT_RUN'
    assert value['formal_collection_allowed'] is False


def manifest_and_assignment():
    modules = ('storm', 'heat', 'snow', 'fade')
    return ({'weather_sequence': list(modules), 'allocation_index': 1,
             'randomization_list_hash': 'synthetic-reference', 'study_stage': 'level_c'},
            AssignmentBundle(1, 'synthetic-reference', modules))


def test_actual_p01_level_c_without_stage_one_decisions():
    manifest, assignment = manifest_and_assignment()
    plan = FixedSequenceProvider().prepare(manifest, assignment)
    assert plan.modules == assignment.weather_sequence
    assert plan.decisions == (None, None, None, None)
    assert load('current-batch.json')['p01_supports_level_c'] is True


def test_actual_p01_level_c_rejects_copied_policy_decisions():
    manifest, assignment = manifest_and_assignment()
    copied = AssignmentBundle(assignment.allocation_index, assignment.randomization_list_hash,
                              assignment.weather_sequence, ({},))
    with pytest.raises(SessionCoreError, match='POLICY_DECISIONS_FORBIDDEN'):
        FixedSequenceProvider().prepare(manifest, copied)


def test_q03_preview_not_actual_batch_or_hidden_allocation():
    preview = json.loads((ROOT / 'agent/tasks/Q-03/outputs/design-cell-preview.json').read_text(encoding='utf-8'))
    assert preview['formal_capable'] is preview['randomized'] is False
    assert preview['participants_observed'] == 0
    assert Counter(c['capacity_batch'] for c in preview['cells']) == {1: 12, 2: 12, 3: 12, 4: 12}
    value = load('current-batch.json')
    q03 = json.loads((ROOT / 'agent/tasks/Q-03/outputs/current-level-c.json').read_text(encoding='utf-8'))
    assert value['planning_anchor'] == q03['planning_anchor']
    assert value['balance_unit'] == q03['balance_unit'] == 'assigned_not_complete'
    assert value['completion_based_refilling_forbidden'] is True
    assert value['fixed_four_batches_required'] is value['per_batch_equal_arm_counts_required'] is False


def test_register_is_empty_and_separates_actual_counts():
    with (TASK / 'outputs/batch-register-template.csv').open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        assert list(reader) == []
        assert {'assigned', 'exposed', 'completed', 'stopped_after_exposure',
                'cancelled_before_exposure', 'pending', 'condition_counts_ref'} <= set(reader.fieldnames)
        assert not {'name', 'phone', 'participant_id', 'hmac', 'password'} & set(reader.fieldnames)


def test_qc_is_not_pass_and_has_required_raw_sources():
    value = load('batch-qc-template.json')
    assert value['status'] == 'NOT_RUN' and value['batch_ref'] is None
    assert all(v is None for v in value['counts'].values())
    assert value['archive_integrity'] == {'status': 'NOT_CHECKED', 'report_ref': None}
    assert value['raw_evidence_bundle']['status'] == 'NOT_CHECKED'
    assert value['raw_evidence_bundle']['report_ref'] is None
    schema = json.loads((ROOT / 'agent/modules/srp_session_store/contracts/raw-evidence-bundle-v1.schema.json').read_text(encoding='utf-8'))
    assert set(value['raw_evidence_bundle']['required_sources']) == set(schema['properties']['families']['items']['enum'])
    assert all(v is None for v in value['review'].values())


def test_exposure_interruption_annotation_and_reporting_boundaries():
    value = load('current-batch.json')
    assert value['one_core_experience_per_person'] is True
    assert value['post_exposure_repeat_allowed'] is value['interruption_resumes_experience'] is False
    assert value['annotation_roles'] == {'independent_annotators': 2, 'adjudicator': 1, 'named_people': []}
    assert value['actual_may_copy_target'] is False
    assert value['primary_affect_reporting_blocked_by_functional_or_scci_failure'] is False
    text = (TASK / 'outputs/current-batch.md').read_text(encoding='utf-8')
    for point in ('教学已可能展示核心材料', '不恢复体验进度', '不强制每批6比6',
                  '尚未完成双人标注时标QC待补', '不能按“完成各24”定向补人', '未知null而非零'):
        assert point in text


def test_input_sources_and_legacy_is_not_duplicated():
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    for path in sources['paths']:
        assert (ROOT / path).exists(), path
    assert not list((TASK / 'archive').glob('19_*.json'))
    assert not list((TASK / 'outputs').glob('*manifest*.json'))
