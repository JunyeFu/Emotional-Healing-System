import copy
import json

import pytest

from validate_current import CURRENT, validate


def fixture():
    return json.loads(CURRENT.read_text(encoding='utf-8'))


def test_current_handoff():
    assert validate(fixture()) == []


@pytest.mark.parametrize('section,key,value', [
    ('camera', 'mode', 'SCROLL'),
    ('camera', 'weather_scroll', True),
    ('camera', 'parallax', True),
    ('camera', 'pause_freezes_motion', False),
    ('assets', 'effects', 'split_background_layers'),
    ('assets', 'reconstruction_required', True),
    ('assets', 'release_requires_license', False),
    ('fade', 'color_source', 'recovery_value'),
    ('fade', 'color_source', 'target_step'),
    ('fade', 'color_scope', 'native_only'),
    ('fade', 'initial_color', 'red_blue_filter'),
    ('fade', 'water_cue_source', 'module_effective_time'),
    ('conditions', 'formal_input', 'same_waveform_both_people'),
    ('conditions', 'native_requires_hidden', True),
    ('conditions', 'exclusive_phase_cues', False),
    ('authority', 'session_clock', 'unity'),
    ('authority', 'touchdesigner', 'required_controller'),
    ('research', 'native_win_required', True),
    ('research', 'report_prespecified_affect_if_function_guard_fails', False),
])
def test_reject_superseded_rules(section, key, value):
    data = copy.deepcopy(fixture())
    data[section][key] = value
    assert f'{section}.{key}' in validate(data)


@pytest.mark.parametrize('index', range(4))
def test_wrong_breathing_mapping(index):
    data = fixture()
    data['modules'][index]['breathing'] = 'other_structure'
    assert validate(data)


def test_duplicate_weather():
    data = fixture()
    data['modules'][3] = copy.deepcopy(data['modules'][0])
    assert 'modules' in validate(data)


def test_old_coarse_phase_contract_is_not_full_demo():
    data = fixture()
    data['runtime_contract'] = 'heat_snow_v2.1_full_demo'
    assert 'runtime_contract' in validate(data)
