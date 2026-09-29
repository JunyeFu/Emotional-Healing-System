"""Read current handoff indices; never freeze or authorize a study."""
import csv
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def report():
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = {row['task_id']: row for row in csv.DictReader(stream)}
    task = rows['U12-11']
    milestone_states = read(GOV / 'audit_upgrade/task_milestone_status_v1.0.json')['statuses']
    freezes = read(ROOT / 'agent/tasks/G-03/outputs/freeze-template.json')['required_freezes']
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        capabilities = list(csv.DictReader(stream))
    required = read(ROOT / 'agent/tasks/G-03/outputs/current-freeze.json')['required_activity_capabilities']
    return {
        'task_id': 'U12-11', 'business_status': task['status'], 'claimant': task['claimant'] or None,
        'reviewer': task['reviewer'] or None,
        'scope': 'CURRENT_HANDOFF_INDEX_NOT_FREEZE_OR_APPROVAL', 'formal_authorization': False,
        'dependencies': [{'id': dep, 'status': milestone_states[dep] if dep in milestone_states else rows[dep]['status']}
                         for dep in task['depends_on'].split('|')],
        'protocol_status': protocol['status'],
        'protocol_formal_collection_allowed': protocol['formal_participant_collection_allowed'],
        'freeze_index_ref': 'agent/tasks/G-03/outputs/freeze-template.json',
        'required_freezes': [{'id': key, **freezes[key]} for key in protocol['required_freezes']],
        'stage1_capabilities': [row for row in capabilities if row['capability_id'] in required],
        'g05_all_capability_count': len(capabilities),
        'formal_parameters': {
            'training_budget_seconds': protocol['training']['budget_seconds'],
            'minimum_important_affect_difference': protocol['primary']['minimum_important_affect_difference'],
            'critical_module_error_thresholds': protocol['functional_guard']['critical_module_error_thresholds'],
            'missingness_model_and_mnar_grid': protocol['missingness']['model_and_mnar_grid'],
            'randomized_n': protocol['sample_planning']['formal_randomized_n'],
            'recruitment_cap': protocol['sample_planning']['formal_recruitment_cap']},
        'candidate_only': {'functional_margin': protocol['functional_guard']['noninferiority_margin_candidate'],
                           'imputations': protocol['missingness']['candidate_imputations'],
                           'power_target': protocol['sample_planning']['main_power_target_candidate']},
        'old_anchors_not_final_power': [protocol['sample_planning'][key] for key in
            ('level_c_anchor', 'stage_1_old_complete_target', 'stage_1_old_recruitment_cap')],
        'real_calibration_status': read(ROOT / 'agent/tasks/A-03/outputs/current-statistics.json')['milestones']['CAL'],
        'real_technical_closeout': read(ROOT / 'agent/tasks/E-03/outputs/current-closeout.json')['technical_closeout'],
        'formal_gate_proved': read(ROOT / 'agent/tasks/U12-09/outputs/current-consistency.json')['formal_gate_proved'],
        'real_parameter_freeze': 'NOT_DELIVERED', 'independent_review': 'NOT_RUN',
        'human_acceptance': 'NOT_SIGNED', 'normalization_is_business_completion': False,
        'root_migration_complete': False}


if __name__ == '__main__':
    (TASK / 'outputs/current-freeze.json').write_text(json.dumps(report(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('WROTE current freeze handoff index; no approval or frozen parameters')
