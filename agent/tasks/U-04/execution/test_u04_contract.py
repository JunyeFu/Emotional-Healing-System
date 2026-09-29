import csv
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U-04'
UNITY = ROOT / 'agent/modules/04-Unity视觉/SRP-Weather-Visual'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def contract():
    return read(TASK / 'outputs/current-adapter.json')


def guid(path):
    return re.search(r'^guid: ([0-9a-f]{32})$', path.read_text(encoding='utf-8-sig'), re.M)[1]


def test_actual_registry_and_owner():
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U-04')
    data = contract()
    assert data['status'] == row['status'] == 'WAIT_DEP'
    assert data['depends_on'] == row['depends_on'].split('|')
    assert data['claimant'] is None and not row['claimant'] and not row['reviewer']
    assert data['acceptance_evidence'] == row['evidence_required'].split(';')


def test_remaining_set_does_not_invent_a_assignment():
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    slice_ = read(ROOT / 'agent/tasks/U-03/outputs/current-slice.json')
    remaining = [m['id'] for m in scenes['modules'] if m['id'] != slice_['selected_weather']]
    data = contract()
    assert data['weather_candidates'] == remaining == ['storm', 'heat', 'snow']
    assert data['selected_weather'] is None
    assert data['allocation_status'] == 'MISSING_V02_EXPLICIT_A_B_C_ASSIGNMENT'
    assert data['template_acceptance'] == slice_['template_freeze'] == 'NOT_COMPLETED'


def test_fixed_camera_and_current_protocol():
    data = contract()
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    config = read(ROOT / 'agent/modules/srp_session_core/config/breath_protocol_config_v2.2.json')
    assert data['camera_mode'] == scenes['camera']['mode'] == 'FIXED'
    assert data['cue_modes'] == scenes['conditions']['modes']
    assert data['runtime_schema_version'] == config['breath_protocol_config_version']
    assert not data['participant_core_input'] and not data['requires_td_or_spout']
    assert data['actual_adapter_acceptance'] == data['performance_acceptance'] == 'NOT_RUN'


@pytest.mark.parametrize('name', ['SetupWeatherScenes', 'SetupWeatherWalkScene'])
def test_legacy_tools_removed_from_assets_and_no_remaining_references(name):
    assert not (UNITY / f'Assets/Scripts/Editor/{name}.cs').exists()
    assert not (UNITY / f'Assets/Scripts/Editor/{name}.cs.meta').exists()
    source = TASK / f'archive/{name}.cs'
    assert 'MenuItem(' in source.read_text(encoding='utf-8-sig')
    identifier = guid(TASK / f'archive/{name}.cs.meta')
    for path in (UNITY / 'Assets').rglob('*'):
        if path.suffix in {'.cs', '.unity', '.prefab', '.asset'}:
            text = path.read_text(encoding='utf-8-sig')
            assert identifier not in text and name not in text, path


def test_old_framework_is_archived_with_current_pointer():
    old = (TASK / 'archive/PROJECT_FRAMEWORK.md').read_text(encoding='utf-8-sig')
    assert 'StormScene (已完成)' in old and 'Spout' in old
    current = (UNITY / 'PROJECT_FRAMEWORK.md').read_text(encoding='utf-8-sig')
    assert 'agent/tasks/U-04/outputs/current-adapter.md' in current
    assert 'StormScene (已完成)' not in current


def test_legacy_storm_scene_is_not_current_four_layer_assembly():
    scene = (UNITY / 'Assets/Scenes/StormScene.unity').read_text(encoding='utf-8-sig')
    refs = set(re.findall(r'm_Script: \{[^\n]*guid: ([0-9a-f]{32})', scene))
    assert guid(UNITY / 'Assets/Scripts/WeatherController.cs.meta') in refs
    assert guid(UNITY / 'Assets/U01/Runtime/U01RuntimeBridge.cs.meta') not in refs
    assert guid(UNITY / 'Assets/Scripts/V03/V03SceneAdapter.cs.meta') not in refs
    for name in ('Traveler', 'Shield', 'WeatherDirector'):
        assert f'm_Name: {name}' in scene


def test_actual_sources_exist_and_stay_inside_repo():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        source = (ROOT / relative).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), relative
