import csv
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U-05'
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        return {r['task_id']: r for r in csv.DictReader(stream)}


def contract():
    return read(TASK / 'outputs/current-adapter.json')


def test_registry_scope_and_unclaimed_status():
    row = rows()['U-05']
    data = contract()
    assert data['status'] == row['status'] == 'WAIT_DEP'
    assert data['depends_on'] == row['depends_on'].split('|')
    assert not row['claimant'] and not row['branch'] and not row['reviewer']
    assert data['claimant'] is None and row['effort_person_days'] == '4'
    assert data['acceptance_evidence'] == row['evidence_required'].split(';')


def test_b_is_not_assigned_from_list_order():
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    slice_ = read(ROOT / 'agent/tasks/U-03/outputs/current-slice.json')
    a = read(ROOT / 'agent/tasks/U-04/outputs/current-adapter.json')
    data = contract()
    remaining = [m['id'] for m in scenes['modules'] if m['id'] != slice_['selected_weather']]
    assert data['weather_label'] == 'B' and data['selected_weather'] is None
    assert data['weather_candidates'] == a['weather_candidates'] == remaining == ['storm', 'heat', 'snow']
    assert data['allocation_status'] == a['allocation_status'] == 'MISSING_V02_EXPLICIT_A_B_C_ASSIGNMENT'
    assert data['template_acceptance'] == slice_['template_freeze'] == 'NOT_COMPLETED'


@pytest.mark.parametrize('weather,seconds,step_ids', [
    ('storm', [3, 3, 3, 3], ['inhale_1', 'hold_1', 'exhale_1', 'hold_2']),
    ('heat', [4, 6], ['inhale_1', 'exhale_1']),
    ('snow', [5, 5], ['inhale_1', 'exhale_1']),
])
def test_candidate_breathing_uses_actual_v22_steps(weather, seconds, step_ids):
    data = contract()
    config = read(ROOT / data['breathing_source'])
    mapping = read(ROOT / data['mapping_source'])
    steps = config['modules'][weather]['steps']
    assert config['breath_protocol_config_version'] == data['runtime_schema_version'] == '2.2'
    assert [s['duration_seconds'] for s in steps] == seconds
    assert [s['step_id'] for s in steps] == step_ids
    assert mapping['weather_profiles'][weather]['runtime_binding'] == 'F-05_V2_2_REQUIRED'
    modes = {r['cue_mode'] for r in mapping['rows'] if r['technical_id'] == weather}
    assert modes == set(data['cue_modes']) == {'scene_native', 'abstract_pacer'}


def test_current_control_roles_and_missing_acceptance():
    data = contract()
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    assert data['camera_mode'] == scenes['camera']['mode'] == 'FIXED'
    assert not data['participant_core_input'] and not data['requires_td_or_spout']
    assert data['clock_authority'] == 'P-01'
    assert data['actual_adapter_acceptance'] == data['performance_acceptance'] == 'NOT_RUN'
    assert not data['formal_collection_allowed']


@pytest.mark.parametrize('name', ['HeatScene', 'SnowScene'])
def test_legacy_scene_has_no_current_bridge_or_four_layer_adapter(name):
    scene = (UNITY / f'Assets/Scenes/{name}.unity').read_text(encoding='utf-8-sig')
    assert 'm_Script:' not in scene
    for object_name in ['Traveler', 'MainCamera', 'PromptDisplay', 'WeatherParticles', 'Background']:
        assert f'm_Name: {object_name}' in scene


@pytest.mark.parametrize('name', ['CleanAndRebuildScenes', 'CleanupWeatherDuplicates'])
def test_archived_tool_bytes_and_no_activity_or_consumers(name):
    original = f'02-技术研发/04-Unity视觉/SRP-Weather-Visual/Assets/Scripts/Editor/{name}.cs'
    assert not (ROOT / original).exists() and not (ROOT / (original + '.meta')).exists()
    archived = TASK / f'archive/{name}.cs'
    assert '[MenuItem(' in archived.read_text(encoding='utf-8-sig')
    # The reviewed pre-migration commit is fixed, so future reruns remain meaningful.
    for suffix in ['', '.meta']:
        result = subprocess.run(['git', 'show', f'16fa5ad:{original}{suffix}'], cwd=ROOT, capture_output=True, check=True)
        assert result.stdout == (TASK / f'archive/{name}.cs{suffix}').read_bytes()
        attr = subprocess.run(['git', 'check-attr', 'text', '--', f'agent/tasks/U-05/archive/{name}.cs{suffix}'],
                              cwd=ROOT, capture_output=True, text=True, check=True)
        assert attr.stdout.rstrip().endswith(': text: unset')
    meta = (TASK / f'archive/{name}.cs.meta').read_text(encoding='utf-8-sig')
    identifier = re.search(r'^guid: ([0-9a-f]{32})$', meta, re.M)[1]
    for path in (UNITY / 'Assets').rglob('*'):
        if path.suffix in {'.cs', '.unity', '.prefab', '.asset'}:
            text = path.read_text(encoding='utf-8-sig')
            assert identifier not in text and name not in text, path


def test_budget_dependency_gap_is_not_an_invented_pass():
    data = contract()
    registry = rows()
    assert 'U-05' in registry['U-08']['depends_on'].split('|')
    assert 'U-08' in registry['U-05']['acceptance_criteria']
    assert data['budget_dependency_issue'] == 'U08_DEPENDS_ON_U05_BUT_U05_AC3_CONSUMES_U08_BUDGET'
    assert data['budget_specification_status'] == 'NOT_AVAILABLE_IN_REVIEWED_INPUTS'
    assert data['performance_acceptance'] == 'NOT_RUN'


def test_source_paths_are_real_and_inside_repo():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), relative
