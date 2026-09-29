"""Check actual writing scope, archived instructions and immutable signatures."""
import csv
import hashlib
import json
from pathlib import Path
import re
import runpy

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def current():
    return read(TASK / 'outputs/current-manuscript.json')

def test_registration_real_results_and_author_gaps():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'W-02')
    assert row['status'] == current()['business_status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == current()['depends_on'] == ['W-01', 'A-06', 'U12-07']
    assert row['claimant'] == row['reviewer'] == ''
    assert current()['real_manuscript'] == 'NOT_DELIVERED'
    assert current()['real_results'] == 'NOT_RUN' and current()['scope_receipt'] is None
    assert read(ROOT / 'agent/tasks/A-06/outputs/current-scope.json')['real_scope_closure'] == 'NOT_RUN'

def test_reporting_scope_matches_live_protocol():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    value = current()
    assert value['primary_outcome'] == protocol['primary']['outcome']
    assert value['contrast'] == protocol['primary']['contrast']
    assert value['primary_reporting_blocked_by_guard_or_scci'] is protocol['functional_guard']['blocks_affect_reporting'] is False
    assert value['native_is_hidden'] is value['not_significant_is_equivalent'] is False
    assert value['equivalence_confirmatory_enabled'] is protocol['equivalence']['confirmatory_enabled'] is False
    assert value['primary_negative_favors'] == 'scene_native'
    assert value['primary_positive_favors'] == 'abstract_pacer'
    assert value['causal_project_vs_no_project_claim_supported'] is False
    assert value['weather_and_breath_structure_independently_identified'] is False

def test_archived_structure_and_validator_consumers():
    archived = TASK / 'archive/00_IJHCI论文结构.md'
    assert hashlib.sha256(archived.read_bytes()).hexdigest().upper() == '27DE3F91CB7EB05C364745210DC3974D412F312F0DB8625CF4AD43B8A9766395'
    old_matrix = TASK / 'archive/01_主张证据矩阵.csv'
    with old_matrix.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8 and 'Gate2组件1' in rows[2]['证据']
    validator = runpy.run_path(str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py'))
    assert archived in validator['ACTIVE_FILES'] and archived in validator['REQUIRED_MARKERS']
    assert old_matrix in validator['ACTIVE_FILES']
    with (PLAN / '25_论文投稿与成果交付/01_主张证据矩阵.csv').open(encoding='utf-8-sig', newline='') as stream:
        active = list(csv.DictReader(stream))
    assert len(active) == 8 and active[0]['ID'] == 'C1' and '负性情绪' in active[0]['主张']
    assert all(row['当前状态'] == 'NOT_RUN' for row in active)
    assert all('Gate2组件' not in row['证据'] for row in active)

def test_u1207_signed_identity_and_conflict_not_overwritten():
    signature = read(GOV / 'u12_upgrade/acceptance/U12-07.json')
    assert signature['candidate_commit'] == '28008f5a4c9963a32488ef32b61dc6ad055562de'
    assert signature['human_review']['reviewer'] == '傅钧烨'
    assert signature['human_review']['status'] == 'PASS'
    impact = (TASK / 'evidence/consumer-impact.md').read_text(encoding='utf-8')
    assert 'FIXED_CURRENT_U1207_SPECIFICATION' in impact and '第180行' in impact
    old = (ROOT / 'agent/tasks/U12-07/archive/signed-candidate/design_method.md').read_text(encoding='utf-8')
    assert '结果必须按门控顺序呈现' in old
    spec = (ROOT / 'agent/tasks/U12-07/outputs/current-method.md').read_text(encoding='utf-8')
    assert 'PANAS' in spec and '非论文正文' in spec
    assert current()['old_u1207_signed_scope_automatically_current'] is False

def test_unobserved_claim_matrix_and_optional_extension():
    matrix = read(TASK / 'outputs/claim-evidence.json')
    assert matrix['status'] == 'NOT_RUN' and matrix['scope_receipt'] is None
    assert len(matrix['rows']) == 8
    for row in matrix['rows']:
        assert row['status'] == 'NOT_RUN'
        assert row['result_ref'] is row['figure_ref'] is None
        assert (ROOT / row['source']).is_file()
    assert current()['requires_unstarted_stage3_done'] is False
    assert current()['actual_stage3_activity_may_be_hidden'] is False
    assert current()['stage3_effect_requires_u1208_results'] is True
    assert current()['actual_sequence_rank_is_causal_effect'] is False

def test_sources_and_active_navigation():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for relative in ('25_论文投稿与成果交付/00_IJHCI论文结构.md',
                     '12_步骤11_离线处理分析与论文写作/00_第11步计划.md'):
        path = PLAN / relative
        assert 'agent/tasks/W-02/outputs/current-manuscript.md' in path.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / link).resolve().exists(), link
    assert current()['normalization_is_business_completion'] is current()['root_migration_complete'] is False
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-manuscript.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
