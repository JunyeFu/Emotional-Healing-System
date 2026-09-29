"""Check current delivery facts and repaired authority, not product release."""
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/Z-01'
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
UNITY = ROOT / '02-技术研发/04-Unity视觉/SRP-Weather-Visual'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


@pytest.fixture
def validator():
    path = PLAN / '99_验证与清单/validate_team_tool_baseline.py'
    spec = importlib.util.spec_from_file_location('z01_team_tools', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_authority_and_direct_pins(validator):
    baseline = read(GOV / 'team_tool_baseline_v1.0.json')
    assert validator.validate_authority(baseline) == []
    assert baseline['workspace'] == '.'
    assert len(baseline['python_direct_dependencies']) == 11


@pytest.mark.parametrize('suffix', ['main', '0' * 40])
def test_floating_or_mismatched_manifest_rejected(validator, tmp_path, monkeypatch, suffix):
    manifest = read(UNITY / 'Packages/manifest.json')
    key = 'com.coplaydev.unity-mcp'
    manifest['dependencies'][key] = manifest['dependencies'][key].rsplit('#', 1)[0] + '#' + suffix
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setattr(validator, 'UNITY_MANIFEST', path)
    assert validator.validate_authority(read(GOV / 'team_tool_baseline_v1.0.json')) == [
        'Unity MCP manifest must pin the same commit as the package lock']


def test_missing_direct_dependency_rejected(validator):
    baseline = copy.deepcopy(read(GOV / 'team_tool_baseline_v1.0.json'))
    del baseline['python_direct_dependencies']['python-osc']
    assert 'Python direct dependency file does not match machine authority' in validator.validate_authority(baseline)


def test_workspace_outside_checkout_rejected(validator):
    baseline = copy.deepcopy(read(GOV / 'team_tool_baseline_v1.0.json'))
    baseline['workspace'] = '..'
    assert validator.validate_authority(baseline) == [f'workspace must match the repository root: {ROOT}']


def test_extras_metadata_uses_distribution_name(validator, monkeypatch):
    queried = []

    def version(name):
        queried.append(name)
        return '4.25.1'

    monkeypatch.setattr(validator.importlib.metadata, 'version', version)
    assert validator.package_version('jsonschema[format]') == '4.25.1'
    assert queried == ['jsonschema']


@pytest.mark.parametrize('name,expected', [
    ('team-tool-baseline-before-z01.json', 'b40e77d107a8d68cab9290fe9cb35c9a907b6e24cfbcdcbc442b2d9a069f9aaa'),
    ('team-tools-before-z01.md', '0f79bbf515ecaa1fd3472b62a488c398042ecd3e241df18453092e9405ca63d7'),
])
def test_archive_original_bytes(name, expected):
    assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest() == expected


def test_registry_and_open_delivery_identity():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(row for row in csv.DictReader(stream) if row['task_id'] == 'Z-01')
    current = read(TASK / 'outputs/current-delivery.json')
    assert row['status'] == current['status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == current['dependencies']
    assert not row['claimant'] and not row['reviewer']
    assert current['candidate_commit'] is None
    assert current['candidate_sbom'] is None
    assert current['python_transitive_lock'] is None
    assert current['clean_checkout_rebuild'] == 'NOT_RUN'
    assert current['formal_use_allowed'] is False


def test_existing_dev_build_does_not_grant_formal_candidate():
    manifest = read(ROOT / 'agent/validation/evidence/F-03/run-1-build-manifest.json')
    assert manifest['build_mode'] == 'DEV-REPLAY'
    assert manifest['formal_use_allowed'] is False
    assert len(manifest['files']) > 0
    source = (UNITY / 'Assets/F03/Editor/F03Build.cs').read_text(encoding='utf-8-sig')
    assert 'BuildOptions.Development' in source
    assert 'formal_use_allowed = false' in source


def test_formal_build_gate_and_sources_remain_real():
    gate = (UNITY / 'Assets/Scripts/Editor/FormalBuildGate.cs').read_text(encoding='utf-8-sig')
    assert 'ValidateAssetGovernance();' in gate
    assert 'FORMAL_RUNTIME_CONTROLLER_MISSING' in gate
    assert 'UNCONTROLLED_DEVELOPMENT_BUILD' in gate
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).exists(), source


def test_tool_changes_are_not_frozen_dispatch_inputs():
    names = {'team_tool_baseline_v1.0.json', '11_团队工具与环境冻结基线_v1.0.md'}
    for manifest in (GOV / '当前解锁独立任务包').glob('*/package_manifest.json'):
        text = manifest.read_text(encoding='utf-8-sig')
        assert not any(name in text for name in names), manifest
    mapping = (GOV / '12_独立任务包文件映射_v1.0.json').read_text(encoding='utf-8-sig')
    assert not any(name in mapping for name in names)
