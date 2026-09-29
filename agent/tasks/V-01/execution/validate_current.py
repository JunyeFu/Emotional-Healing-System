"""Validate current design usage without approving research collection."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
DESIGN = REPO / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def validate(view, protocol, training):
    errors = []
    expected = {
        'status': 'DESIGN_CANDIDATE_NOT_RESEARCH_FROZEN',
        'formal_collection_allowed': False,
        'research_authority_version': protocol['schema_version'],
        'runtime_schema_version': '2.2',
        'participant_rule': {k: protocol['participant_rule'][k] for k in ('one_stage', 'one_condition', 'one_core_experience')},
        'conditions': training['conditions'],
        'native_is_hidden': False,
        'module_ids': ['storm', 'heat', 'snow', 'fade'],
        'module_occurrence': 'exactly_once',
        'sequence_authority': 'python_manifest',
        'clock_authority': 'python_monotonic_clock',
        'unity_reads_questionnaires': False,
        'unity_independent_of_td': True,
        'td_role': 'read_only_monitor',
        'segments': ['demo', 'closed_loop', 'lock_transition'],
        'default_seconds': protocol['core_experience']['segments_seconds'],
        'allowed_seconds': {'demo': [24, 30], 'closed_loop': [140, 160], 'lock_transition': [20, 30]},
        'default_core_seconds': protocol['core_experience']['recommended_total_seconds'],
        'training_budget_seconds': training['formal_training_budget_seconds'],
        'candidate_training_budget_seconds': training['candidate_budget_seconds'],
        'training_counts_in_core_seconds': False,
        'core_demo_replaces_training': False,
        'exposure_boundary': 'before_first_condition_specific_material',
        'exposure_receipt_required_before_training': True,
        'report_affect_if_functional_guard_fails': protocol['primary']['report_even_if_functional_guard_fails'],
        'manipulation_role': protocol['manipulation_check']['role'],
        'stage_3_required_for_core_paper': False,
        'non_timed_core_boundaries': ['J-05', 'J-09'],
        'camera': 'fixed',
        'fade_fullscreen_color_source': 'module_effective_time_not_recovery_or_breath_step',
    }
    for key, value in expected.items():
        if view.get(key) != value:
            errors.append(f'{key} differs from current design authority')
    nodes = view.get('journey', [])
    phases = [n['phase'] for n in nodes]
    expected_phases = ['site_setup', 'neutral_preparation', 'panas_pre', 'condition_training',
                       'neutral_entry', 'module_reveal', 'demo', 'closed_loop', 'lock_transition',
                       'module_transition', 'neutral_completion', 'panas_post',
                       'understanding_and_other_measures', 'data_check']
    if phases != expected_phases:
        errors.append('journey order or completeness differs')
    ids = [n['id'] for n in nodes]
    expected_ids = ['J-01', 'J-02', 'J-03', 'J-03T', 'J-04', 'J-05', 'J-06',
                    'J-07', 'J-08', 'J-09', 'J-10', 'J-11', 'J-11M', 'J-12']
    if ids != expected_ids:
        errors.append('journey IDs do not identify the documented boundaries')
    if len(ids) != len(set(ids)):
        errors.append('duplicate journey ID')
    for node in nodes:
        expected_core = node['phase'] in {'module_reveal', 'demo', 'closed_loop', 'lock_transition', 'module_transition'}
        if node['core'] != expected_core or (node['core'] and node['participant_action'] != 'none'):
            errors.append(f"core timing/action differs: {node['id']}")
    if sum(view['default_seconds'].values()) * len(view['module_ids']) != view['default_core_seconds']:
        errors.append('core duration sum mismatch')
    return errors


def inputs():
    return (load(TASK / 'outputs/current-experience.json'),
            load(DESIGN / '00_总控/protocol_authority_v1.2.json'),
            load(REPO / 'agent/tasks/U12-03/outputs/contract.json'))


if __name__ == '__main__':
    errors = validate(*inputs())
    for error in errors:
        print('ERROR:', error)
    if not errors:
        print('PASS current V-01 design: 14 journey nodes; pre/training/core/post order; 800s; authority and exposure boundary')
    raise SystemExit(bool(errors))
