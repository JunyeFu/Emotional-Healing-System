import csv
import json
from pathlib import Path
import re
import subprocess
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U-08'
UNITY = ROOT / 'agent/modules/04-Unity视觉/SRP-Weather-Visual'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def contract():
    return read(TASK / 'outputs/current-product.json')


def registry():
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        return {r['task_id']: r for r in csv.DictReader(stream)}


def test_business_status_owner_and_required_evidence_unchanged():
    data, row = contract(), registry()['U-08']
    assert data['status'] == row['status'] == 'WAIT_DEP'
    assert data['depends_on'] == row['depends_on'].split('|')
    assert data['claimant'] is None and not row['claimant'] and not row['branch'] and not row['reviewer']
    assert data['acceptance_evidence'] == row['evidence_required'].split(';')


def test_five_adapter_families_cover_eight_weather_condition_cases():
    data = contract()
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    assert data['weather_ids'] == [m['id'] for m in scenes['modules']]
    assert data['cue_modes'] == scenes['conditions']['modes']
    assert data['adapter_families'] == [f'{w}_native' for w in data['weather_ids']] + ['shared_abstract_pacer']
    assert data['render_case_count'] == len(data['weather_ids']) * len(data['cue_modes']) == 8
    assert data['journey_case_count'] == 24 * len(data['cue_modes']) == 48
    assert data['default_core_seconds'] == 800 and not data['training_inside_core']


def test_budget_specification_precedes_upstream_performance_acceptance():
    data, rows = contract(), registry()
    budget = data['budget']
    assert budget['schema_id'] == 'U08_PLANNING_FIELDS_NOT_RUNTIME_CONFIG'
    assert budget['status'] == 'DRAFT_FIELDS_NOT_FROZEN'
    assert budget['provider_task'] == 'U-08' and budget['specification_before_integrated_acceptance']
    for task_id in ['U-04', 'U-05', 'U-06']:
        assert task_id in rows['U-08']['depends_on'].split('|')
        assert 'U-08' in rows[task_id]['acceptance_criteria']
        assert task_id in budget['consumer_tasks']
    for name in ['target_machine', 'gpu_driver', 'display_resolution', 'display_refresh_hz', 'view_distance',
                 'output_device', 'system_output_level', 'minimum_fps', 'maximum_frame_time_ms',
                 'maximum_memory_mb', 'maximum_load_time_seconds', 'profile_version', 'freeze_authorization']:
        assert budget[name] is None
    assert budget['missing_means'] == 'NOT_FROZEN_NOT_ZERO_NOT_PASS'


def test_research_u4_is_not_weather_a_task():
    data = contract()
    source = (PLAN / '00_总控/13_IJHCI独立审稿攻击与升级裁定_v1.1.md').read_text(encoding='utf-8-sig')
    assert 'U4 可访问' in source and '不冻结Unity正式构建' in source
    assert data['accessibility_gate'] == 'RESEARCH_U4_NOT_TASK_U04'
    assert {'not_color_only', 'key_contrast', 'resolution', 'mute', 'reduced_motion'} <= set(data['accessibility_checks'])


def test_formal_and_demo_profiles_not_mixed():
    profiles = contract()['profiles']
    assert not profiles['formal_frozen']['participant_changes']
    assert not profiles['formal_frozen']['session_parameter_changes']
    assert profiles['formal_frozen']['operator_controls'] == ['pause', 'abort']
    assert profiles['demo_accessible']['changes_before_start_only']
    assert not profiles['demo_accessible']['formal_use_allowed']


def test_current_camera_and_color_are_not_legacy_scroll():
    data = contract()
    scenes = read(ROOT / 'agent/tasks/V-02/outputs/current-scenes.json')
    assert data['camera'] == scenes['camera']['mode'] == 'FIXED'
    rules = data['visual_rules']
    assert not rules['scroll'] and not rules['parallax'] and not rules['camera_shake_or_zoom']
    assert not rules['breathing_drives_whole_screen'] and not rules['recovery_forces_success']
    assert rules['fade_color_source'] == scenes['fade']['color_source'] == 'module_effective_time'
    assert data['clock_authority'] == 'P-01' and not data['requires_td_or_spout'] and not data['participant_core_input']


def test_audio_candidate_and_pause_semantics():
    data = contract()
    rules = data['audio_rules']
    assert rules['role'] == 'WEATHER_AMBIENCE_NOT_PHASE_OR_REWARD'
    assert rules['same_condition_track_and_processing'] and rules['pause_freezes_position_and_output']
    assert not rules['resume_restarts_track']
    assert data['audio_limits']['status'] == 'V03_CANDIDATES_NOT_DEVICE_FREEZE'
    assert data['audio_limits']['integrated_loudness_lufs_i'] == [-24, -20]
    assert data['audio_limits']['true_peak_max_dbtp'] == -3
    assert data['audio_limits']['crossfade_seconds'] == [2, 4]


@pytest.mark.parametrize('name', ['BuildScene1', 'BuildScene2D'])
def test_legacy_menu_archived_verbatim_and_no_active_consumers(name):
    relative = f'agent/modules/04-Unity视觉/SRP-Weather-Visual/Assets/Scripts/Editor/{name}.cs'
    assert not (ROOT / relative).exists() and not (ROOT / (relative + '.meta')).exists()
    for suffix in ['', '.meta']:
        before = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['git_source_bytes'](ROOT, '742da55', relative + suffix)
        assert before == (TASK / f'archive/{name}.cs{suffix}').read_bytes()
        attr = subprocess.run(['git', 'check-attr', 'text', '--', f'agent/tasks/U-08/archive/{name}.cs{suffix}'],
                              cwd=ROOT, capture_output=True, text=True, check=True)
        assert attr.stdout.rstrip().endswith(': text: unset')
    code = (TASK / f'archive/{name}.cs').read_text(encoding='utf-8-sig')
    assert '[MenuItem(' in code and 'EditorSceneManager.SaveScene' in code
    assert 'FilterMode.Point' in code and 'spritePixelsPerUnit = 32' in code
    assert 'AddComponent<Scene1Director>()' in code and 'BuildPipeline.BuildPlayer' not in code
    meta = (TASK / f'archive/{name}.cs.meta').read_text(encoding='utf-8-sig')
    guid = re.search(r'^guid: ([0-9a-f]{32})$', meta, re.M)[1]
    for path in (UNITY / 'Assets').rglob('*'):
        if path.suffix in {'.cs', '.unity', '.prefab', '.asset'}:
            value = path.read_text(encoding='utf-8-sig')
            assert name not in value and guid not in value, path


def test_existing_storm_scene_bytes_preserved():
    relative = 'agent/modules/04-Unity视觉/SRP-Weather-Visual/Assets/Scenes/StormScene.unity'
    before = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['git_source_bytes'](ROOT, '742da55', relative)
    assert before == (ROOT / relative).read_bytes()


def test_development_build_is_not_default_or_product_build():
    data = contract()['build']
    settings = (UNITY / 'ProjectSettings/EditorBuildSettings.asset').read_text(encoding='utf-8-sig')
    assert re.findall(r'^    path: (.+)$', settings, re.M) == [data['default_enabled_scene']]
    code = (UNITY / 'Assets/F03/Editor/F03Build.cs').read_text(encoding='utf-8-sig')
    assert 'BuildPipeline.BuildPlayer' in code and 'scenes = new[] { GeneratedScenePath }' in code
    assert 'BuildOptions.Development' in code and 'formal_use_allowed = false' in code
    assert data['actual_product_scene_list'] is None and data['windows_product_acceptance'] == 'NOT_RUN'


def test_formal_gate_and_asset_blocking_are_retained():
    data = contract()['build']
    source = (UNITY / 'Assets/Scripts/Editor/FormalBuildGate.cs').read_text(encoding='utf-8-sig')
    assert data['formal_gate_retained'] and 'ValidateAssetGovernance();' in source
    assert 'UNCONTROLLED_DEVELOPMENT_BUILD' in source and 'FORMAL_SCENES_MISSING' in source
    assert data['current_gate_required_component'] == 'FormalRuntimeController' and 'FormalRuntimeController' in source
    assert data['current_gate_alignment'] == 'PENDING_FINAL_RUNTIME_ASSEMBLY_NOT_BYPASSED'
    original = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['git_source_bytes'](ROOT, '742da55', (UNITY / 'Assets/Scripts/Editor/FormalBuildGate.cs').relative_to(ROOT).as_posix())
    relocated = source.replace('Directory.GetParent(Directory.GetParent(technicalRoot)?.FullName ?? "")?.FullName', 'Directory.GetParent(technicalRoot)?.FullName').replace('"agent", "modules", "07-数据治理"', '"02-技术研发", "07-数据治理"')
    assert original.decode('utf-8-sig').replace('\r\n', '\n') == relocated


def test_design_assets_and_software_done_do_not_prove_license_clearance():
    data = contract()
    preview = read(ROOT / 'agent/tasks/V-04/outputs/current-preview.json')
    assert data['license']['v04_asset_count'] == preview['assets_per_weather'] * 4 == 32
    assert data['license']['all_actual_release_dependencies_required']
    assert data['license']['clearance'] == 'NOT_PROVEN'
    assert data['license']['gate_owner_task'] == 'G-02' and data['license']['real_clearance_owner_task'] == 'G-05'
    assert not data['formal_collection_allowed']


def test_sources_exist_inside_repository():
    for relative in read(TASK / 'inputs/sources.json')['paths']:
        source = (ROOT / relative).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), relative
