"""Read upstream handoff gaps, not a product or public-release decision engine."""
import csv
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def report():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['task_id']: row for row in csv.DictReader(stream)}
    row = registry['U12-12']
    scope = read(ROOT / 'agent/tasks/A-06/outputs/current-scope.json')
    submission = read(ROOT / 'agent/tasks/W-03/outputs/current-submission.json')
    artifact = read(ROOT / 'agent/tasks/Z-01/outputs/current-delivery.json')
    handover = read(ROOT / 'agent/tasks/W-04/outputs/current-handover.json')
    index = read(ROOT / 'agent/tasks/W-04/outputs/handover-index.json')
    return {
        'task_id': 'U12-12', 'business_status': row['status'], 'claimant': row['claimant'] or None,
        'reviewer': row['reviewer'] or None,
        'scope': 'CURRENT_HANDOFF_FACTS_NOT_PRODUCT_OR_PUBLIC_APPROVAL',
        'depends_on': row['depends_on'].split('|'),
        'options': ['scene_native', 'abstract_pacer', 'retain_research_prototype'],
        'selected_option': None, 'real_decision': 'NOT_MADE', 'decision_evidence_ref': None,
        'real_scope_closure': scope['real_scope_closure'],
        'author_consent': submission['author_consent'],
        'upstream_publication_authorized': submission['publication_authorized'],
        'candidate_release_commit': artifact['candidate_commit'],
        'clean_rebuild': artifact['clean_checkout_rebuild'],
        'eight_handover_items': index['items'],
        'actual_handover_package': handover['actual_handover_package'],
        'new_member_handover_exercise': handover['new_member_handover_exercise'],
        'public_release_authorized': False, 'restricted_transfer_authorized': False,
        'automatic_deployment_recommendation': False, 'native_is_default_winning_product': False,
        'independent_review': 'NOT_RUN', 'human_acceptance': 'NOT_SIGNED',
        'normalization_is_business_completion': False, 'root_migration_complete': False}


if __name__ == '__main__':
    (TASK / 'outputs/current-decision.json').write_text(json.dumps(report(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('WROTE current handoff facts; no product selection or public approval')
