"""Check actual package expectations and keep unavailable evidence unavailable."""
import csv
import hashlib
import json
from pathlib import Path
import re

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def test_actual_registry_and_unassigned_roles():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'W-04')
    value = read(TASK / 'outputs/current-handover.json')
    assert row['status'] == value['business_status'] == 'WAIT_DEP'
    assert row['depends_on'].split('|') == value['depends_on'] == ['W-03', 'Z-01', 'U12-12']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['actual_receiver'] is None and value['actual_ip_application_receipt'] is None

def test_eight_delivery_objects_have_no_invented_evidence():
    index = read(TASK / 'outputs/handover-index.json')
    assert index['status'] == 'NOT_DELIVERED'
    assert [i['id'] for i in index['items']] == ['unity', 'python', 'td', 'video', 'poster', 'copyright', 'patent', 'team']
    for item in index['items']:
        assert item['status'] == 'NOT_DELIVERED'
        assert item['actual_path'] is item['byte_hash'] is item['receiver'] is None
        assert (ROOT / item['source']).is_file()

def test_current_scope_does_not_expand_prior_done():
    value = read(TASK / 'outputs/current-handover.json')
    assert value['actual_handover_package'] == 'NOT_DELIVERED'
    assert value['new_member_handover_exercise'] == 'NOT_RUN'
    assert value['deployment_decision'] == 'NOT_OBTAINED'
    for key in ('preview_is_live_e2e', 'python_tests_are_handover_exercise',
                'public_release_authorized', 'restricted_transfer_authorized',
                'native_is_default_winning_product', 'old_fixed_public_order_is_current_authorization',
                'external_award_or_acceptance_guaranteed', 'requires_unstarted_stage3_done',
                'normalization_is_business_completion', 'root_migration_complete'):
        assert value[key] is False, key
    assert read(ROOT / 'agent/tasks/W-03/outputs/current-submission.json')['publication_authorized'] is False

def test_actual_archive_sources_and_navigation():
    archived = TASK / 'archive/03_成果交付与公开顺序.md'
    assert hashlib.sha256(archived.read_bytes()).hexdigest().upper() == '231A0423C326F6AE554A11B5C80FA2F29896628DCC1C3F34A1F94375CBAB6474'
    for source in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / source).is_file(), source
    path = PLAN / '25_论文投稿与成果交付/03_成果交付与公开顺序.md'
    text = path.read_text(encoding='utf-8')
    assert 'agent/tasks/W-04/outputs/current-handover.md' in text
    for link in re.findall(r'\]\(([^)]+)\)', text):
        assert (path.parent / link).resolve().exists(), link
    for path in (TASK / 'TASK.md', TASK / 'outputs/current-handover.md'):
        assert not re.search('诊断|治疗|疾病|患者|医疗设备|临床', path.read_text(encoding='utf-8'))
