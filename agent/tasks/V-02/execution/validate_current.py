"""Check current handoff against the already adopted scene decisions."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DESIGN = REPO / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
V04 = DESIGN / '20_产品与场景设计/V-04_完整分镜与真实时长声音预演'
CURRENT = Path(__file__).resolve().parents[1] / 'outputs/current-scenes.json'
EXPECTED = {
    'authority': {'sequence': 'python_manifest', 'session_clock': 'python', 'touchdesigner': 'optional_read_only', 'participant_core_input': False},
    'camera': {'mode': 'FIXED', 'weather_scroll': False, 'parallax': False, 'pause_freezes_motion': True},
    'conditions': {'modes': ['scene_native', 'abstract_pacer'], 'exclusive_phase_cues': True, 'same_target_events': True, 'same_algorithms': True, 'same_audio': True, 'same_timing': True, 'same_background': True, 'same_cumulative_function': True, 'formal_input': 'each_participant_real_input', 'formative_input': 'same_source', 'abstract_form': 'centered_unfilled_double_ring', 'native_requires_hidden': False},
    'assets': {'background': 'complete_fixed_image', 'effects': 'ai_independent_rgba_assets', 'reconstruction_required': False, 'release_requires_license': True},
    'fade': {'color_scope': 'whole_screen_both_conditions', 'color_source': 'module_effective_time', 'initial_color': 'fully_desaturated', 'restoration_fraction': 0.95, 'water_cue_source': 'target_step_or_actual_estimate', 'recovery_role': 'independent_contour_and_texture', 'pause_freezes_color': True},
    'research': {'native_win_required': False, 'report_prespecified_affect_if_function_guard_fails': True},
}
MODULES = {
    'storm': ('风雨隘口', '雨幕风门', 'box_3_3_3_3'),
    'heat': ('热浪盐原', '冷流风道', 'long_exhale_4_6'),
    'snow': ('雪雾松林', '粉雪升沉', 'equal_inhale_exhale_5_5'),
    'fade': ('彩色湿地（原灰霾湿地概念）', '色潮回流', 'double_inhale_long_exhale'),
}


def validate(data):
    errors = []
    for section, fields in EXPECTED.items():
        for key, value in fields.items():
            if data.get(section, {}).get(key) != value:
                errors.append(f'{section}.{key}')
    for key, value in {
        'task_id': 'V-02', 'formal_collection_allowed': False,
        'runtime_contract': 'F-05_v2.2_all_four_demo_cycle_identity',
        'journey': 'V-01_current_14_nodes_training_outside_core',
        'transition': 'shared_mountain_mist_corridor_not_weather_camera_revision',
    }.items():
        if data.get(key) != value:
            errors.append(key)
    modules = data.get('modules', [])
    indexed = {m['id']: m for m in modules}
    if len(modules) != 4 or set(indexed) != set(MODULES):
        errors.append('modules')
    for module, values in MODULES.items():
        if tuple(indexed.get(module, {}).get(k) for k in ('scene', 'mechanism', 'breathing')) != values:
            errors.append(f'modules.{module}')
    return errors


def main():
    errors = validate(json.loads(CURRENT.read_text(encoding='utf-8')))
    sources = {
        'V-04_H3_四天气固定镜头修订合同_v1.0.md': ['四个天气模块统一采用固定镜头', '不再横向滚动', '局部环境', '暂停时'],
        'V-04_H3_AI独立贴纸素材合同_v1.0.md': ['固定底图保持完整单图', '共32项', '不得从完整背景拆分'],
        'V-04_H3合并评审与Unity交接合同_v1.0.md': ['随模块有效进度连续恢复', '约95%', '不读取呼吸步骤或`recovery_value`', '对四种天气均依赖F-05 v2.2'],
    }
    for name, phrases in sources.items():
        content = (V04 / name).read_text(encoding='utf-8-sig')
        errors.extend(f'source:{name}:{p}' for p in phrases if p not in content)
    journey = json.loads((REPO / 'agent/tasks/V-01/outputs/current-experience.json').read_text(encoding='utf-8'))
    if len(journey['journey']) != 14:
        errors.append('V-01 current journey')
    if errors:
        print('\n'.join(f'ERROR: {error}' for error in errors))
        return 1
    print('PASS: current V-02 handoff; 4 fixed scenes; independent assets; fade time/step/recovery separated; V-01 14 nodes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
