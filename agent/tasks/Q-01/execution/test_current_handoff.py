import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
PACKAGE = PLAN / '20_产品与场景设计/Q-01_LevelA与独立重建'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_current_roles_and_decision_boundary_match_original():
    current = read(TASK / 'outputs/current-level-a.json')
    contract = read(PACKAGE / 'framework_contract_v1.0.json')
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(row for row in csv.DictReader(stream) if row['task_id'] == 'Q-01')
    assert current['business_status'] == row['status'] == 'DONE'
    assert current['role_counts'] == {role: value['count'] for role, value in contract['roles'].items()}
    assert current['cvi_dimensions'] == contract['expert_gate']['required_dimensions']
    assert current['i_cvi_min'] == contract['expert_gate']['i_cvi_min']
    assert current['s_cvi_ave_min'] == contract['expert_gate']['s_cvi_ave_min']
    assert current['real_activity'] == current['final_render_review'] == 'NOT_RUN'
    assert current['current_revision_acceptance'] == 'NOT_SIGNED'
    assert not current['real_people_verified']
    assert not current['affect_comparison_gated_by_reconstruction']


def test_current_degradation_matches_runtime_design():
    current = read(TASK / 'outputs/current-level-a.json')
    mapping = read(ROOT / 'agent/tasks/V-03/outputs/current-mapping.json')
    composition = mapping['confidence_fallback_composition']
    assert current['unusable_actual_display'] == composition['unusable_or_disconnected_rule']
    assert current['fallback_reads_actual_confidence'] == composition['fallback_layer_reads_actual_confidence'] is False
    assert current['unknown_input_may_be_zero_filled'] is False
    assert current['fade_saturation_source'] == 'MODULE_EFFECTIVE_TIME'


def test_sources_and_active_navigation():
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).exists(), path
    for path in (PACKAGE / 'README.md', PACKAGE / '04_课题实际构念与证据矩阵.md',
                 PACKAGE / '07_完整执行SOP与空白报告.md', TASK / 'outputs/current-level-a.md'):
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / link).resolve().exists(), link


def test_archive_bytes_and_signed_sources_unchanged():
    for name, expected in read(TASK / 'inputs/sources.json')['archived_bytes'].items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == expected
    protected = [PACKAGE / name for name in ('framework_contract_v1.0.json',
                 '11_第二人审核报告_已签署.md', '02_盲态独立重建任务书.md',
                 '05_盲态材料母版与编号方案.md', '06_重建真值与评分键.md')]
    changed = subprocess.run(['git', 'diff', '7e6deb4', '--name-only', '--', *map(str, protected)],
                             cwd=ROOT, capture_output=True, text=True, check=True)
    assert not changed.stdout.strip()
    assert not (PACKAGE / 'tools/summarize_q01.py').exists()
    assert not (PACKAGE / 'tools/validate_q01_materials.py').exists()


def test_empty_csv_cli_is_incomplete_and_refuses_overwrite(tmp_path):
    output = tmp_path / 'result.json'
    command = [sys.executable, str(TASK / 'execution/summarize_q01.py')]
    for flag, name in (('--roster', 'roster.csv'), ('--expert', 'expert_reviews.csv'),
                       ('--reconstruction', 'reconstruction_scores.csv'), ('--adjudication', 'adjudications.csv')):
        command.extend((flag, str(PACKAGE / 'templates' / name)))
    command.extend(('--out', str(output)))
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert read(output)['decision'] == 'INCOMPLETE'
    original = output.read_bytes()
    retry = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert retry.returncode != 0
    assert 'FileExistsError' in retry.stderr
    assert output.read_bytes() == original
