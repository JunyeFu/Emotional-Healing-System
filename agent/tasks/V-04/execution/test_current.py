import importlib.util
import json
from pathlib import Path

import pytest

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]


def read(path):
    return json.loads((REPO / path).read_text(encoding='utf-8'))


@pytest.fixture
def current():
    return read('agent/tasks/V-04/outputs/current-preview.json')


def test_current_versions_and_camera(current):
    assert current['camera'] == 'FIXED'
    assert current['background_choices'] == {'storm': 'B', 'heat': 'C', 'snow': 'C', 'fade': 'v5'}
    assert not current['preview_order_is_runtime_sequence']
    assert current['assets_per_weather'] * 4 == 32
    assert not current['formal_use_allowed']


def test_current_journey_not_old_core_preview(current):
    journey = read(current['current_journey_source'])
    assert len(journey['journey']) == 14
    ids = [node['id'] for node in journey['journey']]
    assert ids.index('J-03') < ids.index('J-03T') < ids.index('J-04')
    assert journey['default_core_seconds'] == current['paired_core_preview_seconds'] == 800
    assert not current['core_preview_includes_condition_training']
    assert not journey['training_counts_in_core_seconds']
    assert journey['exposure_boundary'] == 'before_first_condition_specific_material'


def test_fade_matches_upstream(current):
    journey = read(current['current_journey_source'])
    assert current['fade_fullscreen_color_source'] == journey['fade_fullscreen_color_source']
    assert current['runtime_schema_version'] == journey['runtime_schema_version']


def test_tools_migrated_and_report_separated():
    spec = importlib.util.spec_from_file_location('v04_check', TASK / 'execution/verify_historical.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(list(module.ARCHIVE.glob('*.py'))) == 37
    assert not list(module.SOURCE.glob('*.py'))
    from types import SimpleNamespace
    old = SimpleNamespace(__name__='validate_v04_full_duration_animatic', HERE=module.ARCHIVE,
                          REPORT=module.ARCHIVE / 'old.json', LOCK_PATH=module.ARCHIVE / 'lock.json')
    lock = module.RUNTIME / 'toolchain-bindings.json'
    module.bind_module(old, lock)
    assert old.HERE == module.SOURCE
    assert old.LOCK_PATH == lock
    assert old.REPORT == module.RUNTIME / 'full-duration-deep-check.json'


@pytest.mark.parametrize('fault', ['size', 'oid', 'missing'])
def test_lfs_mismatch_rejected(tmp_path, fault):
    from verify_historical import validate_lfs_entry, sha256
    path = tmp_path / 'media.bin'
    path.write_bytes(b'actual media bytes')
    entry = {'name': path.name, 'size': path.stat().st_size, 'oid': sha256(path)}
    if fault == 'missing':
        path.unlink()
    elif fault == 'size':
        entry['size'] += 1
    else:
        entry['oid'] = '0' * 64
    with pytest.raises((AssertionError, FileNotFoundError)):
        validate_lfs_entry(entry, tmp_path)
