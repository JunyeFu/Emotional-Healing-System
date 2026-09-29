import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/U-03'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def contract():
    return read(TASK / 'outputs/current-slice.json')


def test_selection_is_historical_fade_not_default_storm():
    risk = read(PLAN / '20_产品与场景设计/V-03_四层视听映射与资产来源基线/V-03_工程风险评分_v1.0.json')
    assert contract()['selected_weather'] == risk['selected_u03_weather'] == 'fade'
    for scorer in risk['scorers'].values():
        for weather in scorer.values():
            assert weather['total'] == sum(weather['scores'].values())
    assert contract()['selection_scope'] == 'V03_HISTORICAL_DESIGN_HANDOFF_NOT_CURRENT_PERFORMANCE'


def test_registry_dependency_and_real_owner():
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U-03')
    data = contract()
    assert data['status'] == row['status'] == 'WAIT_DEP'
    assert data['depends_on'] == row['depends_on'].split('|')
    assert data['claimant'] is None and not row['claimant'] and not row['reviewer']
    assert data['acceptance_evidence'] == row['evidence_required'].split(';')


def test_steps_are_current_config_not_old_autonomous_breathing():
    config = read(ROOT / '02-技术研发/srp_session_core/config/breath_protocol_config_v2.2.json')
    assert contract()['steps'] == config['modules']['fade']['steps']
    assert contract()['runtime_schema_version'] == config['breath_protocol_config_version']
    assert sum(s['duration_seconds'] for s in contract()['steps']) == 10


def test_fade_and_recovery_follow_current_handoff():
    data = contract()
    mapping = read(ROOT / 'agent/tasks/V-03/outputs/current-mapping.json')
    assert data['camera_mode'] == mapping['camera']['mode'] == 'FIXED'
    for key, value in data['fade_color'].items():
        assert mapping['fade_color_animation'][key] == value
    assert data['recovery_lifecycle'] == mapping['recovery_lifecycle']
    assert data['requires_td_or_spout'] is False
    assert data['template_freeze'] == 'NOT_COMPLETED'
    assert data['actual_slice_acceptance'] == 'NOT_RUN'
    assert data['formal_collection_allowed'] is False


@pytest.mark.parametrize('cue', ['scene_native', 'abstract_pacer'])
def test_two_condition_roles_and_current_background(cue):
    rows = read(ROOT / 'agent/tasks/V-03/outputs/current-mapping.json')['rows']
    selected = {r['layer']: r for r in rows if r['technical_id'] == 'fade' and r['cue_mode'] == cue}
    assert len(selected) == 5
    assert selected['recovery']['visual_carrier'] == contract()['recovery_carrier']
    assert 'target' in selected['actual']['forbidden_coupling']
    assert selected['background']['update_trigger'] == 'SESSION_SEGMENT_AND_FIXED_CAMERA_ENVIRONMENT'
    assert 'SCROLL' not in selected['background']['evidence_hook']


def test_actual_interface_not_claimed_color_renderer():
    bridge = (UNITY / 'Assets/U01/Runtime/U01RuntimeBridge.cs').read_text(encoding='utf-8-sig')
    background = (UNITY / 'Assets/Scripts/V03/Layers/BackgroundPass.cs').read_text(encoding='utf-8-sig')
    assert 'public bool ConfirmRendered(' in bridge
    assert 'public void OnSessionSegmentChanged(' in background
    assert 'SCROLL_TIMELINE' not in background
    assert contract()['current_background_pass'] == 'SEGMENT_HOOK_ONLY_NOT_COLOR_RENDERER'


def test_legacy_design_is_archived_not_current_entry():
    assert not (ROOT / '02-技术研发/04-Unity视觉/场景设计.md').exists()
    archived = (TASK / 'archive/场景设计.md').read_text(encoding='utf-8-sig')
    assert 'Spout' in archived and 'calm_index' in archived
    assert '04-Unity视觉/场景设计.md' not in (ROOT / 'AGENTS.md').read_text(encoding='utf-8-sig')
