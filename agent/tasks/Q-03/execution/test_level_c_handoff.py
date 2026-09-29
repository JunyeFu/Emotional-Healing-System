from collections import Counter
import csv
import hashlib
from itertools import permutations
import json
from pathlib import Path
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / 'agent/modules/08-随机化'))
from srp_randomization import generate_list
from srp_randomization.errors import RandomizationError


def current():
    return json.loads((TASK / 'outputs/current-level-c.json').read_text(encoding='utf-8'))


def test_registry_and_actual_open_milestones():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'Q-03')
    value = current()
    assert value['business_status'] == row['status'] == 'WAIT_DEP_EXTERNAL'
    assert value['depends_on'] == row['depends_on'].split('|')
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is value['historical_acceptance'] is None
    assert value['observed_evidence'] == [] and value['real_activity'] == 'NOT_RUN'
    a03 = json.loads((ROOT / 'agent/tasks/A-03/outputs/current-statistics.json').read_text(encoding='utf-8'))
    assert a03['milestones']['REAL'] == a03['milestones']['CAL'] == 'NOT_DELIVERED'


def test_preview_has_48_cells_two_arms_four_capacity_batches_not_people():
    value = json.loads((TASK / 'outputs/design-cell-preview.json').read_text(encoding='utf-8'))
    assert value['formal_capable'] is value['randomized'] is False
    assert value['participants_observed'] == 0
    cells = value['cells']
    assert len(cells) == 48
    assert [c['design_cell'] for c in cells] == list(range(1, 49))
    assert Counter(c['capacity_batch'] for c in cells) == {1: 12, 2: 12, 3: 12, 4: 12}
    expected = set(permutations(('storm', 'heat', 'snow', 'fade')))
    for arm in ('scene_native', 'abstract_pacer'):
        subset = [c for c in cells if c['condition'] == arm]
        assert len(subset) == 24
        assert {tuple(c['weather_sequence']) for c in subset} == expected
    assert all(not {'session_id', 'participant_id', 'allocation_index', 'stage', 'manifest'} & set(c) for c in cells)


def test_x01_really_rejects_level_c_not_relabelled_stage_1():
    assert current()['x01_supports_level_c'] is False
    with pytest.raises(RandomizationError, match='STAGE_UNSUPPORTED'):
        generate_list('level_c', ('all',), 1, b'q03-test-seed-001')


def test_one_person_once_and_current_nongating_authority():
    value = current()
    protocol = json.loads((PLAN / '00_总控/protocol_authority_v1.2.json').read_text(encoding='utf-8'))
    assert value['planning_anchor']['participants'] == protocol['sample_planning']['level_c_anchor'] == 48
    assert value['planning_anchor']['conditions'] == {'scene_native': 24, 'abstract_pacer': 24}
    assert value['planning_anchor_is_formal_sample_size'] is False
    assert value['one_core_experience_per_person'] is value['one_condition_per_person'] is True
    assert value['cross_stage_overlap_allowed'] is False
    assert value['balance_unit'] == protocol['sequence']['balance_unit'] == 'assigned_not_complete'
    assert value['completion_based_refilling_forbidden'] is True
    assert value['primary_affect_reporting_blocked_by_functional_or_scci_failure'] is False
    assert value['optional_stage_3_required_for_core'] == protocol['stage_2_3']['required_for_core_paper'] is False
    assert value['condition_effect_used_for_calibration'] is False


def test_thresholds_signatures_and_independent_actual_are_not_fabricated():
    value = current()
    assert all(v is None for v in value['thresholds'].values())
    assert value['new_freeze']['status'] == 'NOT_GENERATED'
    assert all(v is None for k, v in value['new_freeze'].items() if k != 'status')
    assert value['annotation_roles'] == {'independent_annotators': 2, 'adjudicator': 1, 'named_people': []}
    assert set(value['annotation_blinded_from']) == {'target_trace', 'cue_condition', 'affect_outcome', 'algorithm_prediction'}
    assert value['actual_may_copy_target'] is False and value['unknown_cycle_step_value'] is None
    assert value['formal_collection_allowed'] is False


def test_actual_archive_bytes_navigation_and_legacy_validator_consumer():
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    for name, digest in sources['archived_bytes'].items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == digest
        navigation = (PLAN / '10_步骤09_LevelC技术预试与预注册' / name).read_text(encoding='utf-8')
        assert 'agent/tasks/Q-03/outputs/current-level-c' in navigation
    validator = (PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py').read_text(encoding='utf-8')
    assert 'LEGACY_LEVEL_C / "00_第9步计划.md"' in validator
    assert 'LEGACY_LEVEL_C / "01_详细执行方案.md"' in validator
    for path in sources['paths']:
        assert (ROOT / path).exists(), path


def test_historical_report_not_used_as_current_two_session_template():
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    path = next(p for p in sources['paths'] if p.endswith('19_LevelC数据质量报告模板.json'))
    old = json.loads((ROOT / path).read_text(encoding='utf-8'))
    assert old['sample']['planned'] == 24 and 'completed_both_sessions' in old['sample']
    text = (TASK / 'outputs/current-level-c.md').read_text(encoding='utf-8')
    assert '禁止向其字段填入新数据' in text
    assert '不要求Q-03提前拿最终CAL造成循环' in text
