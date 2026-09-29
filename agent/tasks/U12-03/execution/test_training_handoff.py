"""Check actual relocation and scoped review without fabricating observations."""
import csv
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
ARCHIVE = TASK / 'archive/candidate'
SOURCES = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
OLD_EVIDENCE = json.loads((ARCHIVE / 'evidence.json').read_text(encoding='utf-8'))
BUILD = runpy.run_path(str(TASK / 'execution/build_evidence.py'))


@pytest.mark.parametrize('name,digest', list(SOURCES['archived_bytes'].items()))
def test_original_bytes(name, digest):
    assert hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest().upper() == digest


@pytest.mark.parametrize('name,digest', list(OLD_EVIDENCE['outputs'].items()))
def test_original_candidate_output_identity(name, digest):
    assert BUILD['text_hash'](ARCHIVE / name) == digest


@pytest.mark.parametrize('path,digest', list(OLD_EVIDENCE['sources'].items()))
def test_original_candidate_source_identity(path, digest):
    raw = subprocess.check_output(['git', 'show', '9317f0b649547c2ae1d900fb39f6f486a9407baa:' + path], cwd=ROOT)
    text = raw.decode('utf-8-sig')
    normalized = '\n'.join(line.rstrip() for line in text.splitlines()) + '\n'
    assert hashlib.sha256(normalized.encode('utf-8')).hexdigest() == digest


@pytest.mark.parametrize('name', ['contract.json', 'teaching.md', 'formative.md', 'observation.template.json'])
def test_active_materials_are_unchanged(name):
    assert (TASK / 'outputs' / name).read_bytes() == (ARCHIVE / name).read_bytes()


def test_review_and_frozen_inputs_unchanged():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'U12-03')
    assert row['status'] == 'IN_REVIEW' and row['claimant'] == 'Codex'
    manifest = json.loads((GOV / '当前解锁独立任务包/U12-03/package_manifest.json').read_text(encoding='utf-8'))
    assert manifest['candidate_identity'] == '9317f0b649547c2ae1d900fb39f6f486a9407baa'
    assert manifest['input_snapshot_id'] == OLD_EVIDENCE['input_snapshot_id']
    assert manifest['input_changed'] is False
    assert not (GOV / 'u12_upgrade/acceptance/U12-03.json').exists()


def test_sources_and_actual_consumers():
    assert all((ROOT / p).is_file() for p in SOURCES['paths'])
    for task in ('G-01', 'E-02', 'Q-02', 'R-01', 'V-01'):
        paths = json.loads((ROOT / f'agent/tasks/{task}/inputs/sources.json').read_text(encoding='utf-8'))['paths']
        assert 'agent/tasks/U12-03/outputs/contract.json' in paths
        assert all((ROOT / p).exists() for p in paths)


def test_current_design_generated_separately():
    assert json.loads((TASK / 'evidence/current-design.json').read_text(encoding='utf-8')) == BUILD['generate']()
    old = GOV / 'u12_upgrade/U12-03_fair_training'
    assert sorted(p.name for p in old.iterdir() if p.is_file()) == ['README.md']
    assert BUILD['generate']()['research_freeze'] == 'PENDING'


def test_current_voice_and_real_data_not_fabricated():
    current = json.loads((TASK / 'outputs/current-training.json').read_text(encoding='utf-8'))
    assert current['human_acceptance'] == 'NOT_SIGNED'
    assert current['voice_timing'] == current['participant_observations'] == 'PENDING'
    assert current['formal_collection_allowed'] is False
