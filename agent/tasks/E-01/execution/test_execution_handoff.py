"""Check the real-activity handoff using synthetic rows, never real experts."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
Q01 = ROOT / 'agent/tasks/Q-01/execution'
sys.path.insert(0, str(Q01))
from summarize_q01 import evaluate  # noqa: E402
from test_summarize_q01 import CONTRACT, roster_rows, expert_rows, reconstruction_rows  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_business_and_activity_scope_match_authorities():
    current = read(TASK / 'outputs/current-execution.json')
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['task_id']: row for row in csv.DictReader(stream)}
    assert current['business_status'] == registry['E-01']['status'] == 'BLOCKED_EXTERNAL'
    assert current['dependencies'] == registry['E-01']['depends_on'].split('|')
    assert registry['Q-01']['status'] == 'DONE'
    assert registry['U12-05']['status'] == 'WAIT_DEP_EXTERNAL'
    assert not registry['E-01']['claimant'] and not registry['E-01']['reviewer']
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        capability = next(row for row in csv.DictReader(stream) if row['capability_id'] == current['activity_capability'])
    assert capability['status'] == current['activity_capability_status'] == 'PENDING_EXTERNAL'
    assert not capability['evidence_ref']
    assert current['real_activity'] == 'NOT_RUN' and current['real_result'] is None
    assert current['new_human_acceptance'] == 'NOT_SIGNED'
    assert not current['real_people_verified'] and not current['requires_entire_g05_done']


def test_counts_and_empty_result_do_not_prove_real_activity():
    current = read(TASK / 'outputs/current-execution.json')
    assert current['role_counts'] == {k: v['count'] for k, v in CONTRACT['roles'].items()}
    assert current['role_total'] == sum(current['role_counts'].values()) == 15
    assert current['expert_rows_expected'] == len(expert_rows()) == 80
    assert current['reconstruction_rows_expected'] == len(reconstruction_rows()) == 16
    assert evaluate([], [], [], CONTRACT)['decision'] == 'INCOMPLETE'
    assert not current['affect_comparison_gated_by_reconstruction']


@pytest.mark.parametrize('dimension', CONTRACT['expert_gate']['required_dimensions'])
@pytest.mark.parametrize('accepted,decision', [(6, 'REVISE'), (7, 'PASS')])
def test_per_dimension_cvi_boundary(accepted, decision, dimension):
    rows = expert_rows()
    for row in rows:
        if row['item_id'] == 'E01' and int(row['reviewer_code'][1:]) > accepted:
            row[dimension] = '2'
    result = evaluate(roster_rows(), rows, reconstruction_rows(), CONTRACT)
    assert result['decision'] == decision
    assert result['expert_gate']['i_cvi_by_dimension'][dimension]['E01'] == accepted / 8


def test_critical_blocker_not_replaced_by_six_of_eight_vote():
    rows = expert_rows()
    rows[0]['critical_blocker'] = '1'
    assert evaluate(roster_rows(), rows, reconstruction_rows(), CONTRACT)['decision'] == 'REVISE'


def test_reconstruction_failure_only_downgrades_design_claim():
    assert evaluate(roster_rows(), expert_rows(), reconstruction_rows({'D01', 'D02'}), CONTRACT)['decision'] == 'DOWNGRADE_TO_FOUR_SCENE_DESIGN_PATTERN'


@pytest.mark.parametrize('name', ['00_第7步计划.md', '01_详细执行方案.md', 'G-01-11_伦理提交执行检查清单.md'])
def test_archived_original_bytes_and_navigation(name):
    expected = read(TASK / 'inputs/sources.json')['archived_bytes'][name]
    assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == expected
    entry = PLAN / '08_步骤07_伦理提交与LevelA' / name
    links = re.findall(r'\]\(([^)]+)\)', entry.read_text(encoding='utf-8'))
    assert links
    for link in links:
        assert (entry.parent / link).resolve().exists(), link
    assert 'agent/tasks/E-01/' in entry.read_text(encoding='utf-8')


def test_source_locations_and_legacy_consumer():
    for name in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / name).exists(), name
    source = (ROOT / 'agent/tasks/G-01/execution/verify.py').read_text(encoding='utf-8')
    assert 'agent/tasks/E-01/archive/G-01-11_' in source
    assert "glob('G-01-11_*.md')" not in source


def test_current_wording_and_no_live_activity_claim():
    text = (TASK / 'TASK.md').read_text(encoding='utf-8') + (TASK / 'outputs/current-execution.md').read_text(encoding='utf-8')
    assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', text)
    for term in ('不计入真实评分', '不能跨角色', '不得由Agent代填PASS', '输入原始字节', '原始分歧', 'INCOMPLETE', 'BLOCKED_EXTERNAL'):
        assert term in text
