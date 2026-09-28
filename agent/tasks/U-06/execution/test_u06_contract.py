import csv
import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U-06'
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        return {r['task_id']: r for r in csv.DictReader(stream)}


def contract():
    return read(TASK / 'outputs/current-adapter.json')


def test_registry_and_actual_owner_are_not_changed():
    data, row = contract(), rows()['U-06']
    assert data['status'] == row['status'] == 'WAIT_DEP'
    assert data['depends_on'] == row['depends_on'].split('|')
    assert data['claimant'] is None and not row['claimant'] and not row['reviewer'] and not row['branch']
    assert data['acceptance_evidence'] == row['evidence_required'].split(';')


def test_c_cannot_be_inferred_when_a_and_b_are_unallocated():
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    slice_ = read(ROOT / 'agent/tasks/U-03/outputs/current-slice.json')
    data = contract()
    assert data['weather_label'] == 'C' and data['selected_weather'] is None
    remaining = [m['id'] for m in scenes['modules'] if m['id'] != slice_['selected_weather']]
    for task_id in ['U-04', 'U-05', 'U-06']:
        handoff = read(ROOT / f'agent/tasks/{task_id}/outputs/current-adapter.json')
        assert handoff['selected_weather'] is None
        assert handoff['weather_candidates'] == remaining == ['storm', 'heat', 'snow']
        assert handoff['allocation_status'] == 'MISSING_V02_EXPLICIT_A_B_C_ASSIGNMENT'
    assert data['template_acceptance'] == slice_['template_freeze'] == 'NOT_COMPLETED'


@pytest.mark.parametrize('weather,seconds,ids', [
    ('storm', [3, 3, 3, 3], ['inhale_1', 'hold_1', 'exhale_1', 'hold_2']),
    ('heat', [4, 6], ['inhale_1', 'exhale_1']),
    ('snow', [5, 5], ['inhale_1', 'exhale_1']),
])
def test_remaining_weather_step_identity_is_v22(weather, seconds, ids):
    data = contract()
    config = read(ROOT / data['breathing_source'])
    mapping = read(ROOT / data['mapping_source'])
    steps = config['modules'][weather]['steps']
    assert data['runtime_schema_version'] == config['breath_protocol_config_version'] == '2.2'
    assert [s['step_id'] for s in steps] == ids
    assert [s['duration_seconds'] for s in steps] == seconds
    assert mapping['weather_profiles'][weather]['runtime_binding'] == 'F-05_V2_2_REQUIRED'


def test_fixed_camera_and_control_authority():
    data = contract()
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    assert data['camera_mode'] == scenes['camera']['mode'] == 'FIXED'
    assert data['cue_modes'] == scenes['conditions']['modes']
    assert data['clock_authority'] == 'P-01'
    assert not data['participant_core_input'] and not data['requires_td_or_spout']
    assert not data['formal_collection_allowed']
    assert data['actual_adapter_acceptance'] == data['performance_acceptance'] == 'NOT_RUN'


@pytest.mark.parametrize('name', ['HeatScene', 'SnowScene'])
def test_legacy_scene_unmodified_and_not_current_adapter(name):
    relative = f'02-技术研发/04-Unity视觉/SRP-Weather-Visual/Assets/Scenes/{name}.unity'
    result = subprocess.run(['git', 'show', f'38d2fb1:{relative}'], cwd=ROOT, capture_output=True, check=True)
    assert result.stdout == (ROOT / relative).read_bytes()
    scene = (ROOT / relative).read_text(encoding='utf-8-sig')
    assert 'm_Script:' not in scene
    assert 'm_Name: Traveler' in scene and 'm_Name: WeatherParticles' in scene


@pytest.mark.parametrize('name', ['FinalBuild', 'FinalRebuild', 'ComprehensiveFix'])
def test_obsolete_menu_is_archived_verbatim_without_consumers(name):
    relative = f'02-技术研发/04-Unity视觉/SRP-Weather-Visual/Assets/Scripts/Editor/{name}.cs'
    assert not (ROOT / relative).exists() and not (ROOT / (relative + '.meta')).exists()
    for suffix in ['', '.meta']:
        result = subprocess.run(['git', 'show', f'38d2fb1:{relative}{suffix}'], cwd=ROOT, capture_output=True, check=True)
        assert result.stdout == (TASK / f'archive/{name}.cs{suffix}').read_bytes()
        attr = subprocess.run(['git', 'check-attr', 'text', '--', f'agent/tasks/U-06/archive/{name}.cs{suffix}'],
                              cwd=ROOT, capture_output=True, text=True, check=True)
        assert attr.stdout.rstrip().endswith(': text: unset')
    code = (TASK / f'archive/{name}.cs').read_text(encoding='utf-8-sig')
    assert '[MenuItem(' in code and 'EditorSceneManager.SaveScene' in code
    assert 'FilterMode.Point' in code and 'spritePixelsPerUnit = 32' in code
    assert 'BuildPipeline.BuildPlayer' not in code
    meta = (TASK / f'archive/{name}.cs.meta').read_text(encoding='utf-8-sig')
    guid = re.search(r'^guid: ([0-9a-f]{32})$', meta, re.M)[1]
    for path in (UNITY / 'Assets').rglob('*'):
        if path.suffix in {'.cs', '.unity', '.prefab', '.asset'}:
            source = path.read_text(encoding='utf-8-sig')
            assert name not in source and guid not in source, path


def test_default_scene_and_actual_dev_builder_do_not_prove_formal_build():
    data = contract()
    settings = (UNITY / 'ProjectSettings/EditorBuildSettings.asset').read_text(encoding='utf-8-sig')
    assert re.findall(r'^    path: (.+)$', settings, re.M) == [data['default_build_scene']]
    build = (UNITY / 'Assets/F03/Editor/F03Build.cs').read_text(encoding='utf-8-sig')
    assert 'BuildPipeline.BuildPlayer' in build and 'scenes = new[] { GeneratedScenePath }' in build
    assert 'BuildOptions.Development' in build and 'formal_use_allowed = false' in build
    assert data['verified_builder_role'] == 'F03_DEV_REPLAY_NOT_WEATHER_OR_FORMAL_BUILD'


def test_budget_dependency_is_not_closed_by_normalization():
    data, registry = contract(), rows()
    assert 'U-06' in registry['U-08']['depends_on'].split('|')
    assert 'U-08' in registry['U-06']['acceptance_criteria']
    assert data['budget_specification_status'] == 'NOT_AVAILABLE_IN_REVIEWED_INPUTS'
    assert data['budget_dependency_issue'] == 'U08_DEPENDS_ON_U06_BUT_U06_AC3_CONSUMES_U08_BUDGET'


def test_all_sources_exist_inside_repo():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), relative
