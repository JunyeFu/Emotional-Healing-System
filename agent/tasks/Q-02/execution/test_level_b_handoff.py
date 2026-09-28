import csv
import json
from pathlib import Path

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'


def current():
    return json.loads((TASK / 'outputs/current-level-b.json').read_text(encoding='utf-8'))


def test_registry_status_roles_and_dependencies_are_not_invented():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'Q-02')
    value = current()
    assert value['business_status'] == row['status'] == 'WAIT_DEP'
    assert value['depends_on'] == row['depends_on'].split('|')
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is value['historical_acceptance'] is None
    assert value['observed_coverage'] == []
    assert value['real_activity'] == value['final_render_review'] == 'NOT_RUN'


def test_real_numbers_and_freeze_conflict_remain_explicit():
    sample = current()['sample_plan']
    assert sample['historical_f02_total_range'] == [24, 32]
    assert sample['e02_registry_people_range'] == [12, 16]
    assert all(sample[k] is None for k in ('frozen_total', 'frozen_per_condition', 'frozen_per_round'))
    assert sample['status'] == 'CONFLICT_REQUIRES_RESEARCH_FREEZE'
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'E-02')
    assert '12至16人' in row['deliverables']


def test_timing_and_no_reexposure_match_actual_training_contract():
    value = current()
    training = json.loads((GOV / 'u12_upgrade/U12-03_fair_training/contract.json').read_text(encoding='utf-8'))
    protocol = json.loads((PLAN / '00_总控/protocol_authority_v1.2.json').read_text(encoding='utf-8'))
    assert value['training_candidate_seconds'] == training['candidate_budget_seconds'] == 180
    assert value['training_frozen_seconds'] is training['formal_training_budget_seconds'] is None
    assert value['one_condition_per_person'] == protocol['participant_rule']['one_condition'] is True
    assert value['one_core_experience_per_person'] is True
    assert value['repeat_exposure_for_revision_allowed'] is False
    assert value['thinking_aloud_in_core'] == training['understanding_in_core'] is False
    assert value['question_timing'] == 'AFTER_PANAS_POST_IN_FULL_FLOW'
    assert value['formative_only_data_is_affect_trial_data'] is False
    assert value['timing']['time_to_mastery_seconds'] is None
    assert value['timing']['time_to_mastery_reason'] == 'NOT_MEASURED'
    assert value['timing']['interview_probes_in_self_response_budget'] is False
    assert value['timing']['panas_in_self_response_budget'] is False


def test_current_roles_do_not_block_primary_affect_reporting():
    value = current()
    protocol = json.loads((PLAN / '00_总控/protocol_authority_v1.2.json').read_text(encoding='utf-8'))
    assert value['scci_role'] == protocol['manipulation_check']['role'] == 'manipulation_only'
    assert value['understanding_blocks_affect_reporting'] is False
    assert value['guesses_drop_valid_panas'] is False
    assert protocol['primary']['report_even_if_functional_guard_fails'] is True
    assert value['formal_collection_allowed'] == protocol['formal_participant_collection_allowed'] is False


@pytest.mark.parametrize('name,required', [
    ('responses.csv', {'response_status', 'material_version', 'clip_ref', 'build_ref', 'response_started_ns',
                       'response_ended_ns', 'probe_duration_ns', 'help_count', 'help_duration_ns', 'source_ref'}),
    ('revisions.csv', {'coder_1', 'coder_2', 'disagreement', 'decision', 'reason', 'denominator',
                      'old_version', 'new_version', 'paired_check_ref', 'retest_ref', 'owner'}),
])
def test_templates_are_blank_and_preserve_required_observations(name, required):
    with (TASK / 'outputs' / name).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        assert required <= set(reader.fieldnames)
        assert list(reader) == []
        assert not {'phone', 'name', 'hmac', 'email', 'contact'} & set(reader.fieldnames)
    assert current()['missing_states'] == ['RESPONDED', 'SKIPPED', 'TIMEOUT', 'TECH_UNPRESENTED']
    assert current()['missing_correct_value'] is None


def test_candidate_participant_materials_have_all_four_layers_without_private_keys():
    value = current()
    materials = json.loads((ROOT / '02-技术研发/srp_step_measurement/evidence/participant_items.json').read_text(encoding='utf-8'))
    keys = json.loads((ROOT / '02-技术研发/srp_step_measurement/evidence/private_answer_keys.json').read_text(encoding='utf-8'))
    assert set(value['structures']) == {'storm', 'heat', 'snow', 'fade'}
    assert value['participant_receives_answer_key'] is False
    assert len(materials) == 15 and len(keys) == 30
    for material in materials:
        assert [i['item_id'] for i in material['items']] == value['item_ids']
        assert {i['layer'] for i in material['items']} == {'target', 'actual', 'cumulative', 'degraded'}
        assert 'answer_key' not in material and 'truth' not in material
        assert all('correct' not in i and 'answer' not in i for i in material['items'])


def test_current_instructions_keep_guesses_open_and_sources_resolvable():
    guide = (TASK / 'outputs/interview-guide.md').read_text(encoding='utf-8')
    assert '不问未见过的“第一种还是第二种”' in guide
    assert '不删除有效情绪回答' in guide
    assert '第二轮用新人' in guide
    assert all(code in guide for code in ('STEP_INSTANCE_CONFUSION', 'CYCLE_CONFUSION',
                                          'ACCESSIBILITY_FAILURE', 'ANSWER_KEY_MISMATCH'))
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    for path in sources['paths']:
        assert (ROOT / path).exists(), path
    assert current()['execution_owner'] is current()['freeze_owner'] is None
    assert current()['coding_owners'] == []
