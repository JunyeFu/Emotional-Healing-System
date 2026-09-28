"""Check current closeout handoff and the observed Level C scope repair."""
import csv
import json
from pathlib import Path
import re

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_registry_dependencies_and_absence_of_real_results():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'E-03')
    value = read(TASK / 'outputs/current-closeout.json')
    assert value['business_status'] == row['status'] == 'BLOCKED_EXTERNAL'
    assert value['depends_on'] == row['depends_on'].split('|') == ['Q-03', 'E-02', 'B-01']
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is value['historical_acceptance'] is None
    assert value['actual_batches'] == [] and value['observed_counts'] is None
    assert value['real_activity'] == 'NOT_RUN' and value['formal_collection_allowed'] is False


def test_level_c_activity_explicitly_includes_real_collection_not_only_closeout():
    with (GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    row = next(r for r in rows if r['capability_id'] == 'INSTITUTION_LEVEL_C')
    assert row['activity'].split('|') == ['B-01', 'E-03']
    assert row['status'] == 'PENDING_EXTERNAL' and row['evidence_ref'] == ''
    assert len(rows) == 13
    assert all(r['status'] == 'PENDING_EXTERNAL' for r in rows)


def test_frozen_inputs_are_not_replaced_and_actual_impact_is_recorded():
    impact = read(GOV / 'audit_upgrade/input_impacts/E03_LevelC_activity_scope.json')
    assert impact['research_authorized'] is impact['frozen_packages_replaced'] is False
    assert impact['source_changed_is_runtime_interception'] is False
    for item in impact['affected_tasks']:
        package = GOV / '当前解锁独立任务包' / item['task_id']
        manifest = read(package / 'package_manifest.json')
        assert manifest['input_snapshot_id'] == item['input_snapshot_id']
        assert manifest['status'] == item['status']
        frozen_input = (package / 'inputs/06_task_input.json').read_text(encoding='utf-8-sig')
        assert '6f3d58c0f8179892bce663ace3d18637b6696dce5fc252053c1320e003faaefd' in frozen_input


def test_empty_outline_is_not_evaluated_or_frozen():
    value = read(TASK / 'outputs/closeout-template.json')
    assert value['status'] == 'NOT_RUN' and value['metrics'] == []
    assert all(v is None for v in value['counts'].values())
    assert value['all_batches_qc'] == {'status': 'NOT_EVALUATED', 'report_ref': None}
    assert all(v is None for v in value['review'].values())
    for key in ('technical_configuration_ref', 'calibration_receipt_ref', 'research_freeze_ref', 'formal_randomized_n'):
        assert value[key] is None
    assert {'denominator', 'threshold_source', 'threshold_version', 'observed_value',
            'missing_reason', 'structure_step_quality_scope'} <= set(value['metric_record_fields'])


def test_calibration_dependency_not_reversed_and_formal_n_is_unfrozen():
    milestones = read(GOV / 'audit_upgrade/task_milestones_v1.2.json')
    # The existing milestone schema is consumed, not a new registry.
    cal = next(m for m in milestones['milestones'] if m['id'] == 'A-03-CAL')
    assert 'E-03' in cal['depends_on'] and 'A-03-REAL' in cal['depends_on']
    state = read(TASK / 'outputs/current-closeout.json')
    assert state['required_upstream_cal_milestone'] == 'REAL_NOT_FINAL_CAL'
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    assert protocol['sample_planning']['formal_randomized_n'] is state['formal_randomized_n'] is None
    assert protocol['stage_2_3']['required_for_core_paper'] is False


def test_threshold_units_and_missing_measurements_are_not_substituted():
    s02 = read(ROOT / 'agent/tasks/S-02/outputs/current-events.json')
    q03 = read(ROOT / 'agent/tasks/Q-03/outputs/current-level-c.json')
    assert s02['cycle_f1_minimum'] == .85
    assert s02['boundary_mae_maximum_seconds'] == .50
    assert s02['online_offline_pf_tolerance'] is None
    assert all(v is None for v in q03['thresholds'].values())
    state = read(TASK / 'outputs/current-closeout.json')
    assert state['actual_may_copy_target'] is state['external_latency_from_render_receipt'] is False
    assert state['condition_effect_used_for_calibration'] is False
    assert state['primary_affect_reporting_blocked_by_functional_or_scci_failure'] is False
    text = (TASK / 'outputs/current-closeout.md').read_text(encoding='utf-8')
    for point in ('周期F1与逐步骤事件F1不是同一指标', '同一批数据用于调参后的表现不得伪装为独立验证',
                  '未知cycle/step保留null', '现有A-03正式计分/门仍拒绝', 'NOT_EVALUATED/INCOMPLETE'):
        assert point in text


def test_current_step_nine_navigation_and_sources():
    for name in ('00_第9步计划.md', '01_详细执行方案.md'):
        path = PLAN / '10_步骤09_LevelC技术预试与预注册' / name
        text = path.read_text(encoding='utf-8-sig')
        assert 'agent/tasks/E-03/outputs/current-closeout.md' in text
        assert 'agent/tasks/B-01/outputs/current-batch.md' in text
        for link in re.findall(r'\]\(([^)]+)\)', text):
            assert (path.parent / link).resolve().exists(), link
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).exists(), path
