"""Test navigation, preserved originals and truthful policy/reproduction states."""
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

def test_registry_roles_and_real_delivery():
    value = read(TASK / 'outputs/current-submission.json')
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'W-03')
    assert row['status'] == value['business_status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == value['depends_on'] == ['W-02', 'Z-01', 'G-05']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['actual_submission_package'] == 'NOT_DELIVERED'
    assert value['author_consent'] == 'NOT_OBTAINED' and value['submission_receipt'] is None
    assert value['publication_authorized'] is False

def test_official_read_is_not_submission_day_or_journal_mandate():
    review = read(TASK / 'evidence/official-review.json')
    value = read(TASK / 'outputs/current-submission.json')
    assert review['journal_instructions']['status'] == 'UNVERIFIED_403'
    assert review['submission_day_check'] == value['submission_day_policy_check'] == 'NOT_RUN'
    assert value['journal_anonymity_mode'] == value['journal_data_policy_level'] == 'UNVERIFIED'
    assert value['journal_instructions_verified'] is value['basic_policy_is_journal_mandate'] is False
    assert value['manuscript_initial_draft_by'] == 'REAL_AUTHORS'
    assert value['ai_drafting_is_allowed_by_checked_guidance'] is False
    for key in ('basic_policy', 'ai_policy', 'ai_use_guidance', 'image_policy'):
        assert review[key]['status'] == 'READ' and review[key]['url'].startswith('https://')
    assert '真实作者起草' in (ROOT / 'agent/tasks/W-02/outputs/current-manuscript.md').read_text(encoding='utf-8')

def test_actual_archive_and_legacy_consumer():
    expected = {
        '02_投稿返修检查表.md': '7462F3D12AE85D7FD393588281EA029648ACB12805DD8563527F345C849DEC72',
        '00_第12步计划.md': '8036ACE53336614DE0E6C02CBEC2EA4CB1D78B1157CB7DF67207159DE1106024',
        '01_详细执行方案.md': '60462D619A9552DDA41028025FA2BC2F97CB1DE72A5D6A8388FFAF0A03DC2600',
    }
    for name, digest in expected.items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == digest
    validator = runpy.run_path(str(PLAN / '99_验证与清单/validate_protocol_authority_v1_1.py'))
    assert TASK / 'archive/02_投稿返修检查表.md' in validator['ACTIVE_FILES']

def test_reproduction_and_actual_route_still_open():
    value = read(TASK / 'outputs/current-submission.json')
    assert value['independent_clean_rebuild'] == value['real_analysis_reproduction'] == 'NOT_RUN'
    assert value['synthetic_run_is_real_result_reproduction'] is value['python_tests_are_independent_clean_rebuild'] is False
    assert value['requires_unstarted_stage3_done'] is False
    assert value['g05_route_conflict'] == 'OPEN_ACTIVITY_VS_WHOLE_TASK_ADMISSION'
    assert value['ai_stimuli_are_observed_results'] is False
    assert value['normalization_is_business_completion'] is value['root_migration_complete'] is False

def test_sources_navigation_and_terms():
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    for relative in ('25_论文投稿与成果交付/02_投稿返修检查表.md',
                     '13_步骤12_投稿返修发表与归档/00_第12步计划.md',
                     '13_步骤12_投稿返修发表与归档/01_详细执行方案.md'):
        path = PLAN / relative
        text = path.read_text(encoding='utf-8')
        assert 'agent/tasks/W-03/outputs/current-submission.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            if not link.startswith('https://'):
                assert (path.parent / link).resolve().exists(), link
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-submission.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
