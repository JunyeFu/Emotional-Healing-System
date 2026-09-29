import pytest

from build_current import current_mapping
from validate_current import validate
from validate_historical import historical_authority
import generate_historical


@pytest.mark.parametrize('index', range(40))
def test_every_mapping_row_rejects_source_or_semantic_drift(index):
    data = current_mapping()
    assert not validate(data)
    row = data['rows'][index]
    if row['layer'] == 'background':
        row['source_fields'] = ['target_progress']
    else:
        row['source_fields'] = ['wrong_source']
    assert 'rows' in validate(data)


@pytest.mark.parametrize('section,key,value', [
    ('camera', 'mode', 'SCROLL'),
    ('camera', 'parallax', True),
    ('assets', 'effects', 'split_background_layers'),
    ('fade_color_animation', 'color_source', 'recovery_value'),
    ('fade_color_animation', 'color_source', 'target_step'),
    ('recovery_lifecycle', 'segment_change_resets_recovery', True),
    ('recovery_lifecycle', 'same_module_locked_value_can_resume', True),
    ('recovery_lifecycle', 'force_success_endpoint', True),
])
def test_current_rules(section, key, value):
    data = current_mapping()
    data[section][key] = value
    assert section in validate(data)


@pytest.mark.parametrize('weather', ['storm', 'heat', 'snow', 'fade'])
def test_all_weather_need_instance_binding(weather):
    data = current_mapping()
    data['weather_profiles'][weather]['runtime_binding'] = 'V2_1_COARSE_PHASE_DIRECT'
    assert 'weather_profiles' in validate(data)


def test_fade_recovery_cannot_control_color():
    data = current_mapping()
    row = next(r for r in data['rows'] if r['technical_id'] == 'fade' and r['layer'] == 'recovery')
    row['visual_carrier'] = 'OUTLINE_TEXTURE_AND_BASE_COLOR_COMPLETENESS'
    assert 'rows' in validate(data)


def test_no_duplicate_mapping():
    data = current_mapping()
    data['rows'][1] = data['rows'][0].copy()
    assert 'rows' in validate(data)


def test_historical_bytes_reject_wrong_hash():
    with pytest.raises(AssertionError, match='signed authority bytes mismatch'):
        historical_authority('agent/modules/04-Unity视觉/SRP-Weather-Visual/Packages/manifest.json', '0' * 64)


def test_generator_never_targets_signed_originals(monkeypatch):
    written = []
    monkeypatch.setattr(generate_historical, 'write_json', lambda path, payload: written.append(path))
    generate_historical.main()
    assert len(written) == 5
    assert all(path.parent == generate_historical.Path(__file__).resolve().parents[1] / 'outputs/historical-rebuild' for path in written)
    assert all(not path.is_relative_to(generate_historical.BASE) for path in written)
