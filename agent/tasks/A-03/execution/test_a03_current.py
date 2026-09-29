import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
sys.path.insert(0, str(ROOT / '02-技术研发/02-信号处理'))
from a03_gate2_spec import GateEvidence, GateResult, evaluate_ordered_gate, score_panas


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


@pytest.mark.parametrize('name', ['README_spec_legacy.md', '08_sample_size_anchors.py'])
def test_archived_bytes_match_migration_source(name):
    expected = read_json(TASK / 'inputs/sources.json')['archived_byte_hashes'][name]
    assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == expected


def test_scope_records_actual_u12_04_candidate_acceptance_not_freeze():
    scope = read_json(GOV / 'u12_upgrade/A-03_scope_impact.json')
    actual = read_json(GOV / 'u12_upgrade/acceptance/U12-04.json')
    acceptance = scope['human_acceptance_of_new_spec']
    for field in ('candidate_commit', 'signature_commit', 'date'):
        assert acceptance[field] == actual[field]
    assert acceptance['reviewer'] == actual['human_review']['reviewer']
    assert acceptance['status'] == actual['human_review']['status']
    assert scope['status'] == 'NEW_SPEC_CANDIDATE_ACCEPTED_REAL_CAL_PENDING'
    current = read_json(TASK / 'outputs/current-statistics.json')
    assert current['milestones']['REAL'] == current['milestones']['CAL'] == 'NOT_DELIVERED'
    assert current['historical_simulation']['formal_sample_size'] is None


def test_frozen_dispatch_identity_and_original_candidate_are_preserved():
    manifest = read_json(GOV / '当前解锁独立任务包/A-03/package_manifest.json')
    sources = read_json(TASK / 'inputs/sources.json')
    assert manifest['input_snapshot_id'] == sources['frozen_input_snapshot_id']
    assert manifest['candidate_identity'] == '4071c84bc03ab9d80f7ce5997034fe27737e5d51'
    git_bytes = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['git_source_bytes']
    for path in (GOV / '当前解锁独立任务包').rglob('*'):
        if path.is_file():
            original = git_bytes(ROOT, 'HEAD', path.relative_to(ROOT).as_posix())
            assert original.replace(b'\r\n', b'\n') == path.read_bytes().replace(b'\r\n', b'\n'), path


def test_actual_formal_modes_are_not_enabled_by_fixture_receipt():
    receipt = {'evidence_class': 'SYNTHETIC_ONLY', 'status': 'FIXTURE', 'config_sha256': 'A' * 64}
    with pytest.raises(ValueError, match='PANAS_FORMAL_SCORING_REQUIRES_A03_CAL'):
        score_panas([], positive_item_ids=['P1'], negative_item_ids=['N1'],
                    evaluation_mode='formal', fixture_receipt=receipt)
    result = evaluate_ordered_gate(GateEvidence(*([GateResult.PASS] * 6)),
                                   evaluation_mode='formal', fixture_receipt=receipt)
    assert result['reason_code'] == 'A03_CAL_NOT_DONE'


def cli(output):
    return subprocess.run([
        sys.executable, '-m', 'a03_gate2_spec.simulation', '--output', str(output),
        '--seed', '17', '--replications', '100', '--per-condition', '2',
    ], cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / '02-技术研发/02-信号处理'),
                    'PYTHONIOENCODING': 'utf-8'}, capture_output=True, text=True, encoding='utf-8')


def test_cli_refuses_existing_report_and_preserves_all_bytes(tmp_path):
    output = tmp_path / 'signed.json'
    original = b'SIGNED ORIGINAL\r\n'
    output.write_bytes(original)
    result = cli(output)
    assert result.returncode != 0
    assert 'FileExistsError' in result.stderr
    assert output.read_bytes() == original


def test_cli_creates_new_synthetic_report(tmp_path):
    output = tmp_path / 'new.json'
    result = cli(output)
    assert result.returncode == 0, result.stderr
    report = read_json(output)
    assert report['evidence_class'] == 'SYNTHETIC_ONLY'
    assert report['formal_margins'] is report['formal_sample_size'] is None
    assert report['participants_per_condition'] == 2


def test_all_sources_and_current_module_links_resolve():
    for path in read_json(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).exists(), path
    import re
    path = ROOT / '02-技术研发/02-信号处理/a03_gate2_spec/README.md'
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        assert (path.parent / link).resolve().exists(), link
