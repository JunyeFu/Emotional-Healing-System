import csv
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U-07'
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'
OLD_SPEC = PLAN / '20_产品与场景设计/06_抽象双环对照规格.md'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def contract():
    return read(TASK / 'outputs/current-abstract.json')


def test_registry_owner_and_evidence_remain_actual():
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U-07')
    data = contract()
    assert data['status'] == row['status'] == 'WAIT_DEP'
    assert data['depends_on'] == row['depends_on'].split('|')
    assert data['claimant'] is None and not row['claimant'] and not row['branch'] and not row['reviewer']
    assert data['acceptance_evidence'] == row['evidence_required'].split(';')


def test_v02_form_and_control_authority():
    data = contract()
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    assert data['form'] == scenes['conditions']['abstract_form'] == 'centered_unfilled_double_ring'
    assert data['cue_modes'] == scenes['conditions']['modes']
    assert data['condition_phase_cues_exclusive'] == scenes['conditions']['exclusive_phase_cues']
    assert data['camera_mode'] == scenes['camera']['mode'] == 'FIXED'
    assert data['clock_authority'] == 'P-01'
    assert not data['participant_core_input'] and not data['requires_td_or_spout']
    assert not data['abstract_background_leaks_phase']


@pytest.mark.parametrize('weather', ['storm', 'heat', 'snow', 'fade'])
def test_four_structure_steps_derive_from_v22_not_coarse_phase(weather):
    data = contract()
    config = read(ROOT / data['breathing_source'])
    steps = config['modules'][weather]['steps']
    profile = data['weather_profiles'][weather]
    assert data['runtime_schema_version'] == config['breath_protocol_config_version'] == '2.2'
    assert profile['steps'] == [s['step_id'] for s in steps]
    assert profile['seconds'] == [s['duration_seconds'] for s in steps]
    if weather == 'storm':
        assert profile['steps'][1] != profile['steps'][3]
    if weather == 'fade':
        assert steps[0]['phase'] == steps[1]['phase'] == 'inhale'
        assert profile['steps'][0] != profile['steps'][1]


def test_layer_independence_and_empty_actual():
    layers = contract()['layers']
    assert layers['target']['carrier'] == 'outer_ring'
    assert layers['actual']['carrier'] == 'inner_ring'
    assert layers['actual']['source'].startswith('independent_actual_')
    assert layers['actual']['empty_step'] == 'HIDDEN_NOT_TARGET_COPY'
    assert layers['target']['empty_step'] == 'NO_STEP_ANIMATION'
    assert not layers['recovery']['segment_change_resets']
    assert not layers['recovery']['force_success_endpoint']
    code = (UNITY / 'Assets/Scripts/V03/Layers/ActualLayerAdapter.cs').read_text(encoding='utf-8-sig')
    assert 'if (view.IsEmptyStep)' in code and 'Hide();' in code


def test_four_state_fallback_is_not_generic_ring_fade():
    rules = contract()['layers']['fallback']
    mapping = read(ROOT / contract()['mapping_source'])['confidence_fallback_composition']
    assert rules['carrier'] == 'actual_only'
    assert rules['good'] == 'NO_EXTRA_MARKER'
    assert rules['degraded'] == 'ACTIVE_LOW_CERTAINTY'
    assert rules['unusable_or_disconnected'] == 'STATIC_BROKEN_OUTLINE_LAST_VALID_GEOMETRY'
    assert rules['visible_certainty'] == 'MIN_ACTUAL_CONFIDENCE_ENVELOPE_AND_STATE_CAP'
    assert not mapping['fallback_layer_reads_actual_confidence']
    assert mapping['exact_cap_freeze_gate'] == 'U-03_DEGRADED_VISIBILITY_EVIDENCE'
    assert rules['cap_status'].startswith('CANDIDATE_')


def test_fade_time_color_is_not_ring_or_recovery_success():
    color = contract()['fade_color']
    source = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')['fade']
    assert color['scope'] == source['color_scope']
    assert color['source'] == source['color_source'] == 'module_effective_time'
    assert color['initial'] == source['initial_color'] == 'fully_desaturated'
    assert color['restoration_fraction'] == source['restoration_fraction'] == 0.95
    assert color['pause_freezes'] == source['pause_freezes_color']
    assert color['recovery_role'] == 'OUTLINE_AND_TEXTURE_ONLY'


def test_matching_does_not_require_different_participants_identical_waveforms():
    data = contract()
    assert len(set(data['required_match'])) == 12
    assert {'target_events', 'reward_timing', 'input_algorithm', 'event_truth'} <= set(data['required_match'])
    assert data['formative_input'] == 'same_source'
    assert data['formal_input'] == 'each_participant_real_input_same_algorithm'
    assert data['confounds'] == ['motion', 'brightness', 'complexity', 'eccentricity', 'occlusion', 'event_salience']
    assert data['confound_limits'] == 'HISTORICAL_ENGINEERING_CANDIDATES_NOT_FROZEN'


def test_u03_minimal_counterpart_is_not_blocked_by_u07_promotion():
    data = contract()
    slice_ = read(ROOT / 'agent/tasks/U-03/outputs/current-slice.json')
    assert data['minimal_counterpart_before_promotion'] == 'U-03_FADE'
    assert data['template_acceptance'] == slice_['template_freeze'] == 'NOT_COMPLETED'
    assert 'U-07' not in slice_['depends_on']
    assert data['actual_four_structure_configuration'] == 'NOT_IMPLEMENTED_IN_REVIEWED_INPUTS'
    assert data['actual_render_acceptance'] == 'NOT_RUN' and not data['formal_collection_allowed']


def test_legacy_prompt_is_kept_because_it_still_has_a_caller():
    prompt = (UNITY / 'Assets/Scripts/PromptDisplay.cs').read_text(encoding='utf-8-sig')
    controller = (UNITY / 'Assets/Scripts/WeatherController.cs').read_text(encoding='utf-8-sig')
    assert 'ShowPrompt(string text)' in prompt and 'TextMeshProUGUI' in prompt
    assert 'public PromptDisplay promptDisplay;' in controller and 'promptDisplay.ShowPrompt(' in controller
    assert contract()['existing_prompt_role'] == 'LEGACY_TEXT_FADE_NOT_ABSTRACT_ADAPTER'


def test_existing_legal_r01_examples_only_cover_storm():
    folder = PLAN / '20_产品与场景设计/R-01_四层表示方案/fixtures'
    files = sorted(p.name for p in folder.glob('valid-*.json'))
    assert files == ['valid-storm-abstract-pacer.json', 'valid-storm-scene-native.json']
    assert contract()['existing_r01_fixture_modules'] == ['storm']


def test_original_specification_archived_verbatim():
    relative = OLD_SPEC.relative_to(ROOT).as_posix()
    original = subprocess.run(['git', 'show', f'2e9498a:{relative}'], cwd=ROOT, capture_output=True, check=True).stdout
    assert original == (TASK / 'archive/06_抽象双环对照规格.md').read_bytes()
    pointer = OLD_SPEC.read_text(encoding='utf-8-sig')
    assert 'U-07' in pointer and '当前四态规则' in pointer
    for link in re.findall(r'\]\(([^)]+)\)', pointer):
        assert (OLD_SPEC.parent / link).resolve().is_file(), link


def test_sources_are_current_or_explicit_history():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        source = (ROOT / relative).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), relative
