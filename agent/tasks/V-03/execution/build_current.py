"""Derive the current design handoff without rewriting signed v1.0."""
import copy
import json
from pathlib import Path

from generate_historical import BASE, UNITY_MANIFEST

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def current_mapping():
    data = copy.deepcopy(json.loads((BASE / 'V-03_四层视听映射合同_v1.0.json').read_text(encoding='utf-8')))
    scenes = json.loads((REPO / 'agent/tasks/V-02/outputs/current-scenes.json').read_text(encoding='utf-8'))
    data['schema_id'] = 'V03_CURRENT_USAGE_NOT_NETWORK_MESSAGE'
    data['version'] = '1.2-member-standard'
    standard_path = 'agent/design/weather/2026-10-08_Storm与纯粒子双环实施标准.json'
    standard = json.loads((REPO / standard_path).read_text(encoding='utf-8'))
    data['implementation_standard_source'] = standard_path
    data['unity_target_version'] = standard['unity_target']['version']
    data['abstract_rendering'] = standard['abstract_pacer']
    data['status'] = 'DESIGN_HANDOFF_NOT_RENDERED_EVIDENCE'
    data['runtime_binding_boundary'] = {'all_four_complete_demo': 'F-05_V2_2_REQUIRED', 'unity_is_clock_authority': False}
    data['camera'] = scenes['camera']
    data['assets'] = scenes['assets']
    data['fade_color_animation'] = scenes['fade']
    data['recovery_lifecycle'] = {
        'reset_on': ['session_id', 'module_id', 'module_position'],
        'segment_change_resets_recovery': False,
        'same_module_locked_value_can_resume': False,
        'force_success_endpoint': False,
    }
    data['formal_collection_allowed'] = False
    for profile in data['weather_profiles'].values():
        profile['runtime_binding'] = 'F-05_V2_2_REQUIRED'
    data['weather_profiles']['fade']['recovery'] = 'OUTLINE_AND_TEXTURE_ONLY'
    data['weather_profiles']['storm']['background'] = 'STREAMSIDE_CABIN_NON_PERIODIC_ENVIRONMENT'
    data['weather_profiles']['storm']['scene'] = standard['storm']['scene']
    for row in data['rows']:
        layer = row['layer']
        if row['technical_id'] == 'storm' and layer == 'background':
            row['visual_carrier'] = 'STREAMSIDE_CABIN_NON_PERIODIC_ENVIRONMENT'
        if row['cue_mode'] == 'abstract_pacer' and layer in ('target', 'actual'):
            row['visual_carrier'] = 'PARTICLE_OUTER_RING_CORE' if layer == 'target' else 'PARTICLE_INNER_RING_CORE'
            row['decorative_periphery'] = 'FLOW_SWAY_DELAYED_SCALE_NOT_STEP_TRUTH'
        if row['cue_mode'] == 'abstract_pacer' and layer == 'fallback':
            row['visual_carrier'] = 'PARTICLE_INNER_RING_CERTAINTY_WRAPPER'
        if layer == 'background':
            row['update_trigger'] = 'SESSION_SEGMENT_AND_FIXED_CAMERA_ENVIRONMENT'
            row['evidence_hook'] = 'FIXED_CAMERA_PAUSE_AND_PERIOD_LEAKAGE_REVIEW'
        if layer in ('target', 'actual'):
            row['runtime_slot_binding'] = 'F-05_V2_2_REQUIRED'
            row['source_fields'] += [f'{layer}_cycle_index', f'{layer}_step_id']
        if row['technical_id'] == 'fade' and layer == 'recovery':
            row['visual_carrier'] = 'OUTLINE_AND_TEXTURE_ONLY'
            row['forbidden_coupling'] += ['whole_screen_color_animation']
    return data


def asset_drift():
    original = json.loads((BASE / 'V-03_资产来源与替换台账_v1.0.json').read_text(encoding='utf-8'))
    old = {e['asset_id'].removeprefix('PKG::'): e['hash_or_version'] for e in original['entries'] if e['category'] == 'DIRECT_PACKAGE'}
    current = json.loads(UNITY_MANIFEST.read_text(encoding='utf-8'))['dependencies']
    return {
        'historical_direct_packages': len(old), 'current_direct_packages': len(current),
        'removed': sorted(set(old) - set(current)), 'added': sorted(set(current) - set(old)),
        'version_changes': {k: {'old': old[k], 'current': current[k]} for k in sorted(set(old) & set(current)) if old[k] != current[k]},
        'historical_design_entries': original['design_entry_count'],
        'current_asset_route': 'complete_background_and_32_independent_assets_from_V04',
        'formal_license_clearance': 'NOT_ESTABLISHED_BY_V03',
        'instance_registration_owner': 'G-02/U-08',
    }


def main():
    (TASK / 'outputs').mkdir(exist_ok=True)
    for name, value in [('current-mapping.json', current_mapping()), ('asset-drift.json', asset_drift())]:
        (TASK / 'outputs' / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('WROTE current design mapping=40 rows and asset drift; signed files untouched')


if __name__ == '__main__':
    main()
